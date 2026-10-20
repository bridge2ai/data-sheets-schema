"""Private durable writer for a freshly reconstructed native stage proposal.

The public capture boundary must first verify its actual pending advance and
captured authority. These functions never select a run or create a controller.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from dataclasses import replace
import os
import shlex
import tempfile

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema.native_attempt_supervisor import durable_new, _sync_directory
from data_sheets_schema.native_execution import _mkdir_durable
from data_sheets_schema.native_shared_evidence import read_regular


def proposal_publications(invocation,proposal,*,_catalogs=None):
    """Independently derive all effects before opening any output file."""
    if type(invocation) is not c.StageInvocationCapture:
        raise ValueError('publication requires an exact captured stage invocation')
    catalogs=stage.nr._catalog_context(_catalogs)
    selected=(invocation.selection,invocation.execution,invocation.phase1,invocation.history)
    advance=invocation.current_advance
    argv=(invocation.execution.registered_python,'-m','data_sheets_schema.native_shared_stage',
          'advance','--registration',invocation.selection.registration.pin.path)
    if (advance.argv!=argv or advance.command!=shlex.join(argv)
            or advance.working_directory!=invocation.execution.working_directory
            or advance.call.tool_name!='Bash'
            or advance.call.session_id!=invocation.execution.session_id
            or advance.predecessor_history_sha256!=invocation.history.journal.pin.sha256):
        raise ValueError('publisher invocation differs from current selected advance/history')
    if type(proposal) is c.StageDecision:
        expected=stage._prepare_next(*selected,catalogs)
        if proposal!=expected:
            raise ValueError('publication decision differs from fresh pure reconstruction')
        publications=proposal.publications
    elif type(proposal) is c.StageTransition:
        current=stage._prepare_next(*selected,catalogs)
        if current.state!='awaiting_response' or current.request is None:
            raise ValueError('response publication has no current consumed request')
        expected=stage._check_response(*selected,current.request.raw,proposal.first_response.raw,catalogs)
        if proposal!=expected:
            raise ValueError('publication transition differs from first captured response')
        publications=proposal.publications+tuple(c.HelperPublication(action='create_once',artifact=item,
            predecessor_sha256=None) for item in proposal.records_to_append)+(c.HelperPublication(
            action='replace_journal_from_exact_predecessor',artifact=proposal.predicted_journal,
            predecessor_sha256=invocation.history.journal.pin.sha256),)
    else:
        raise ValueError('publisher accepts only a freshly derived decision or transition')
    paths=[pub.artifact.pin.path for pub in publications]
    if len(paths)!=len(set(paths)):
        raise ValueError('proposal publishes a destination more than once')
    journal=[i for i,pub in enumerate(publications) if pub.action=='replace_journal_from_exact_predecessor']
    if publications and journal!=[len(publications)-1]:
        raise ValueError('publication must end in one exact-predecessor journal replacement')
    root=PurePosixPath(invocation.selection.role('stage_root'))
    for pub in publications:
        path=PurePosixPath(pub.artifact.pin.path)
        if root not in path.parents or any(path in PurePosixPath(other).parents for other in paths if other!=str(path)):
            raise ValueError('proposal destination is outside or overlaps selected stage roles')
        if pub.action=='replace_journal_from_exact_predecessor' and (
                pub.artifact.pin.path!=invocation.selection.role('journal')
                or pub.predecessor_sha256!=invocation.history.journal.pin.sha256):
            raise ValueError('proposal names a foreign journal predecessor')
    return publications


def _physical_destination(path,root):
    c.canonical_path(path,'publication path');c.canonical_path(root,'stage root')
    destination=Path(path);directory=Path(root)
    if (not directory.is_dir() or directory.is_symlink() or directory.resolve()!=directory
            or directory not in destination.parents or destination.resolve()!=destination):
        raise ValueError('publication path is not below its exact regular stage root')
    return destination


def _journal_owner_guard(destination,before,after,owner_context):
    if owner_context is None:
        return
    from . import native_shared_capture as capture
    from . import native_stream_coordination_v1 as coordination
    if type(owner_context) is not coordination._OwnerReaderContext:
        raise ValueError('selected journal requires its exact owner reader context')
    association=owner_context._association
    capture._require_owner_association(owner_context,association.selection,association.execution_raw,
                                      association.started_raw)
    expected=association.selection.role('journal')
    if (str(destination)!=expected or type(before) is not c.CapturedArtifact
            or type(after) is not c.ProposedArtifact
            or before.pin.role!='journal' or after.pin.role!='journal'
            or before.pin.path!=expected or after.pin.path!=expected):
        raise ValueError('selected journal replacement differs from its owner selection')


def _replace_journal(destination,before,after,*,owner_context=None):
    """CAS over exact observed bytes, with exclusive partial file and parent fsync.

    All stage writers share the actual pending-advance boundary. This does not
    claim atomic protection against an unrelated process modifying the host.
    A failed partial file is intentionally retained as incomplete evidence.
    """
    _journal_owner_guard(destination,before,after,owner_context)
    current=read_regular(str(destination),'journal',max_bytes=c.HARD_LIMITS['journal_bytes'])
    if current.captured!=before:
        raise ValueError('journal changed before its checked replacement')
    _journal_owner_guard(destination,before,after,owner_context)
    fd,temporary=tempfile.mkstemp(prefix='journal.partial-',dir=destination.parent)
    if owner_context is None:
        with os.fdopen(fd,'wb') as stream:
            stream.write(after.raw);stream.flush();os.fsync(stream.fileno())
    else:
        try:
            # Unbuffered selected writes cannot be resumed by close() after
            # a later owner refusal. A partial positive write stays failed.
            stream=os.fdopen(fd,'wb',buffering=0)
        except BaseException:
            try:
                os.close(fd)
            except BaseException:
                pass
            raise
        try:
            _journal_owner_guard(destination,before,after,owner_context)
            written=stream.write(after.raw)
            if type(written) is not int or written!=len(after.raw):
                raise OSError('selected journal staging write was incomplete')
            _journal_owner_guard(destination,before,after,owner_context)
            stream.flush()
            _journal_owner_guard(destination,before,after,owner_context)
            os.fsync(stream.fileno())
        except BaseException:
            try:
                stream.close()
            except BaseException:
                pass
            raise
        else:
            stream.close()
    # Check actual bytes AND opened metadata immediately before replacement.
    _journal_owner_guard(destination,before,after,owner_context)
    if read_regular(str(destination),'journal',max_bytes=c.HARD_LIMITS['journal_bytes'])!=current:
        raise ValueError('journal changed while its replacement was being persisted')
    _journal_owner_guard(destination,before,after,owner_context)
    os.replace(temporary,destination)
    _journal_owner_guard(destination,before,after,owner_context)
    _sync_directory(destination.parent)
    observed=read_regular(str(destination),'journal',max_bytes=c.HARD_LIMITS['journal_bytes'])
    if observed.captured.pin!=after.pin or observed.captured.raw!=after.raw:
        raise ValueError('published journal differs from its proposed bytes')
    _journal_owner_guard(destination,before,after,owner_context)
    return observed


def _invocation_owner_guard(invocation,owner_context):
    if owner_context is not None:
        from . import native_shared_capture as capture
        capture._require_owner_association(owner_context,invocation.selection,
            invocation.execution.execution.raw,invocation.execution.started.raw)


def publish_derived(invocation,proposal,*,owner_context=None,_catalogs=None):
    """Publish only reconstructed effects after all destinations pass preflight.

    Selected calls independently recheck their current captured invocation,
    including direct calls. Default pure-component behavior is unchanged. No caller paths or
    alternate command, cursor, journal, session or worker can be selected here.
    """
    from . import native_shared_capture as capture
    if capture._stage_owner_selected(invocation):
        invocation=capture._fresh_stage_invocation(invocation,owner_context,_catalogs=_catalogs)
    elif owner_context is not None:
        raise ValueError('default publication cannot use a selected owner context')
    catalogs=stage.nr._catalog_context(_catalogs)
    publications=proposal_publications(invocation,proposal,_catalogs=catalogs)
    _invocation_owner_guard(invocation,owner_context)
    root=invocation.selection.role('stage_root')
    for pub in publications:
        _invocation_owner_guard(invocation,owner_context)
        destination=_physical_destination(pub.artifact.pin.path,root)
        if pub.action=='create_once':
            if destination.exists() or destination.is_symlink():
                raise ValueError('stage output already exists; partial publication cannot retry')
        else:
            if read_regular(str(destination),'journal',max_bytes=c.HARD_LIMITS['journal_bytes']).captured!=invocation.history.journal:
                raise ValueError('stage journal differs before any proposed output write')
    observed=[]
    for pub in publications:
        _invocation_owner_guard(invocation,owner_context)
        destination=_physical_destination(pub.artifact.pin.path,root)
        if pub.action=='create_once':
            _invocation_owner_guard(invocation,owner_context)
            _mkdir_durable(destination.parent)
            _invocation_owner_guard(invocation,owner_context)
            durable_new(destination,pub.artifact.raw)
            actual=read_regular(str(destination),pub.artifact.pin.role,max_bytes=max(1,pub.artifact.pin.bytes))
            if actual.captured.pin!=pub.artifact.pin:
                raise ValueError('published output differs from proposed complete bytes')
        else:
            actual=(_replace_journal(destination,invocation.history.journal,pub.artifact)
                    if owner_context is None else _replace_journal(destination,invocation.history.journal,
                                                                  pub.artifact,owner_context=owner_context))
        _invocation_owner_guard(invocation,owner_context)
        observed.append(actual)
    after=next((item.captured.pin.sha256 for item in observed if item.captured.pin.role=='journal'),
               invocation.history.journal.pin.sha256)
    after_journal=next((item.captured for item in observed if item.captured.pin.role=='journal'),
                       invocation.history.journal)
    updated=replace(invocation.history,journal=after_journal,
        records=invocation.history.records+tuple(item.captured for item in observed if item.captured.pin.role=='record'),
        artifacts=invocation.history.artifacts+tuple(item.captured for item in observed
            if item.captured.pin.role not in ('record','journal')))
    # Report the actual reconstructed state after publication, never the
    # earlier proposal's state or an unobserved next helper's effects.
    state=stage._prepare_next(invocation.selection,invocation.execution,invocation.phase1,updated,catalogs).state
    result={'kind':c.KINDS['advance_result'],'version':c.VERSION,
        'selection_sha256':invocation.selection.registration.pin.sha256,
        'execution_sha256':invocation.execution.execution.pin.sha256,
        'attempt_id':invocation.execution.attempt_id,'session_id':invocation.execution.session_id,
        'advance_tool_use_id':invocation.current_advance.call.tool_use_id,
        'before_history_sha256':invocation.history.journal.pin.sha256,
        'after_history_sha256':after,'state':state,
        'publications':[c.pin_dict(item.captured.pin) for item in observed]}
    if owner_context is not None:
        c.canonical(result)
        _invocation_owner_guard(invocation,owner_context)
    return result,tuple(observed)
