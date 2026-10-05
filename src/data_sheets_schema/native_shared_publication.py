"""Private durable writer for a freshly reconstructed native stage proposal.

The public capture boundary must first verify its actual pending advance and
captured authority. These functions never select a run or create a controller.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import os
import shlex
import tempfile

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema.native_attempt_supervisor import durable_new, _sync_directory
from data_sheets_schema.native_execution import _mkdir_durable
from data_sheets_schema.native_shared_evidence import read_regular


def proposal_publications(invocation,proposal):
    """Independently derive all effects before opening any output file."""
    if type(invocation) is not c.StageInvocationCapture:
        raise ValueError('publication requires an exact captured stage invocation')
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
        expected=stage.prepare_next(*selected)
        if proposal!=expected:
            raise ValueError('publication decision differs from fresh pure reconstruction')
        publications=proposal.publications
    elif type(proposal) is c.StageTransition:
        current=stage.prepare_next(*selected)
        if current.state!='awaiting_response' or current.request is None:
            raise ValueError('response publication has no current consumed request')
        expected=stage.check_response(*selected,current.request.raw,proposal.first_response.raw)
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


def _replace_journal(destination,before,after):
    """CAS over exact observed bytes, with exclusive partial file and parent fsync.

    All stage writers share the actual pending-advance boundary. This does not
    claim atomic protection against an unrelated process modifying the host.
    A failed partial file is intentionally retained as incomplete evidence.
    """
    current=read_regular(str(destination),'journal',max_bytes=c.HARD_LIMITS['journal_bytes'])
    if current.captured!=before:
        raise ValueError('journal changed before its checked replacement')
    fd,temporary=tempfile.mkstemp(prefix='journal.partial-',dir=destination.parent)
    with os.fdopen(fd,'wb') as stream:
        stream.write(after.raw);stream.flush();os.fsync(stream.fileno())
    # Check actual bytes AND opened metadata immediately before replacement.
    if read_regular(str(destination),'journal',max_bytes=c.HARD_LIMITS['journal_bytes'])!=current:
        raise ValueError('journal changed while its replacement was being persisted')
    os.replace(temporary,destination)
    _sync_directory(destination.parent)
    observed=read_regular(str(destination),'journal',max_bytes=c.HARD_LIMITS['journal_bytes'])
    if observed.captured.pin!=after.pin or observed.captured.raw!=after.raw:
        raise ValueError('published journal differs from its proposed bytes')
    return observed


def publish_derived(invocation,proposal):
    """Publish only reconstructed effects after all destinations pass preflight.

    Used solely by native_shared_capture.publish_stage after its current
    invocation/context and unchanged-authority checks. No caller paths or
    alternate command, cursor, journal, session or worker can be selected here.
    """
    publications=proposal_publications(invocation,proposal)
    root=invocation.selection.role('stage_root')
    for pub in publications:
        destination=_physical_destination(pub.artifact.pin.path,root)
        if pub.action=='create_once':
            if destination.exists() or destination.is_symlink():
                raise ValueError('stage output already exists; partial publication cannot retry')
        else:
            if read_regular(str(destination),'journal',max_bytes=c.HARD_LIMITS['journal_bytes']).captured!=invocation.history.journal:
                raise ValueError('stage journal differs before any proposed output write')
    observed=[]
    for pub in publications:
        destination=_physical_destination(pub.artifact.pin.path,root)
        if pub.action=='create_once':
            _mkdir_durable(destination.parent)
            durable_new(destination,pub.artifact.raw)
            actual=read_regular(str(destination),pub.artifact.pin.role,max_bytes=max(1,pub.artifact.pin.bytes))
            if actual.captured.pin!=pub.artifact.pin:
                raise ValueError('published output differs from proposed complete bytes')
        else:
            actual=_replace_journal(destination,invocation.history.journal,pub.artifact)
        observed.append(actual)
    after=next((item.captured.pin.sha256 for item in observed if item.captured.pin.role=='journal'),
               invocation.history.journal.pin.sha256)
    state=proposal.state if type(proposal) is c.StageDecision else proposal.disposition
    result={'kind':c.KINDS['advance_result'],'version':c.VERSION,
        'selection_sha256':invocation.selection.registration.pin.sha256,
        'execution_sha256':invocation.execution.execution.pin.sha256,
        'attempt_id':invocation.execution.attempt_id,'session_id':invocation.execution.session_id,
        'advance_tool_use_id':invocation.current_advance.call.tool_use_id,
        'before_history_sha256':invocation.history.journal.pin.sha256,
        'after_history_sha256':after,'state':state,
        'publications':[c.pin_dict(item.captured.pin) for item in observed]}
    return result,tuple(observed)
