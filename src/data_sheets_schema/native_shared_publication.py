"""Input-only reconstruction of native stage publications.

Durable effects live in native_shared_publication_orchestration. There is no
consumer-to-orchestrator import or compatibility forwarding entry point.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
import shlex
from . import native_shared_contract as c
from . import native_shared_stage as stage

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
