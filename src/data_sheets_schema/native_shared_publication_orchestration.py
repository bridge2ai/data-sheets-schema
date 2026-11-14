"""Private durable writer for a freshly reconstructed native stage proposal.

The public capture boundary must first verify its actual pending advance and
captured authority. These functions never select a run or create a controller.
"""
from __future__ import annotations

from pathlib import Path
from dataclasses import replace
import os
import tempfile

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema.native_attempt_supervisor import durable_new, _sync_directory
from data_sheets_schema.native_execution import _mkdir_durable
from data_sheets_schema.native_shared_evidence import read_regular
from .native_shared_publication import proposal_publications, _physical_destination


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


def publish_derived(invocation,proposal,*,_catalogs=None):
    """Publish only reconstructed effects after all destinations pass preflight.

    Used solely by native_shared_capture.publish_stage after its current
    invocation/context and unchanged-authority checks. No caller paths or
    alternate command, cursor, journal, session or worker can be selected here.
    """
    catalogs=stage.nr._catalog_context(_catalogs)
    publications=proposal_publications(invocation,proposal,_catalogs=catalogs)
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
    return result,tuple(observed)
