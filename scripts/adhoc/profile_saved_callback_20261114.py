"""Issue 6233: profile read-only callback reconstruction from a stopped synthetic run.

2026-11-14. Inputs: saved execution registration and output directory.
Outputs: cProfile statistics and JSON; no launch, reservation or evidence writes.
This isolated replay does not run under or replace the public-test profile guard.
"""
import argparse
import cProfile
import json
from pathlib import Path
import pstats
import time

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_execution_registration_v2 as registration
from data_sheets_schema import native_shared_controller_orchestration as controller
from data_sheets_schema import native_shared_callback_orchestration as callbacks
from data_sheets_schema import native_shared_controls_orchestration as controls
from data_sheets_schema import native_shared_selection as selections


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('registration', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    raw = args.registration.read_bytes()
    # Exercise ordinary capture before nested source-loader scopes, as the
    # public fixture does; forward annotations resolve in their owning module.
    body = json.loads(raw)['registration']
    composition_body = json.loads(body['composition_raw_json'])
    selected_body = json.loads(composition_body['selection_raw_json'])
    selections.capture(selected_body['registration_path'])
    with authority.launch_derivations():
        with controls.loaded_controls() as projection:
            execution = registration.verified(raw, classifier_projection=projection)
        composition, spec, selection = controller.reconstruct_composition(
            execution['composition_raw_json'].encode())
        with callbacks.preloaded_callbacks(composition, spec, selection, execution, raw,
                                          controller.render.commands(spec)) as resources:
            profiler = cProfile.Profile()
            before = time.monotonic()
            error = None
            try:
                profiler.enable()
                run = resources.capture._load_live(selection.registration.pin.path,
                    _admission=resources.admission, _catalogs=resources.catalogs)
                run.decision()
            except Exception as exc:
                error = type(exc).__name__ + ': ' + str(exc)
            finally:
                profiler.disable()
                elapsed = time.monotonic() - before
                profiler.dump_stats(str(args.output / 'callback.pstats'))
                stats = pstats.Stats(profiler)
                rows = [{'file': key[0], 'line': key[1], 'name': key[2],
                         'calls': counts[1], 'self': counts[2], 'inclusive': counts[3]}
                        for key, counts in stats.stats.items()]
                rows.sort(key=lambda row: -row['inclusive'])
                result = {'wall_seconds': elapsed, 'error': error, 'functions': rows,
                          'scope': 'Isolated fresh callback replay, not a public completion run.'}
                (args.output / 'profile.json').write_text(json.dumps(result, indent=2))
                with (args.output / 'profile.txt').open('w') as stream:
                    stats.stream = stream
                    stats.sort_stats('cumulative').print_stats(60)
                print(json.dumps({'wall_seconds': elapsed, 'error': error}))


if __name__ == '__main__':
    main()
