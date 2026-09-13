"""A runtime library inside the checkout remains a third-party file."""
from pathlib import Path

import pytest

from data_sheets_schema import resources


@pytest.mark.parametrize("relative", [False, True])
def test_checkout_local_runtime_keeps_third_party_identity(tmp_path, monkeypatch, relative):
    import sysconfig
    monkeypatch.chdir(tmp_path)
    library = tmp_path / ".venv/lib/python3.12/site-packages"
    module = library / "another_package/module.py"
    module.parent.mkdir(parents=True)
    module.write_text("# synthetic third-party module\n")
    monkeypatch.setattr(resources, "CHECKOUT_ROOT", tmp_path)
    original = sysconfig.get_path
    monkeypatch.setattr(sysconfig, "get_path", lambda name: str(library) if name in {"purelib", "platlib"} else original(name))
    source = module.relative_to(tmp_path) if relative else module
    assert resources.repo_relative(source) == str(module)
    assert resources.repo_relative(source, cwd=False) == str(module)
    # A caller's corpus and this package's own code keep their established
    # identities; the runtime-library boundary does not swallow either.
    own = resources.PACKAGE_ROOT / "resources.py"
    assert resources.repo_relative(own).endswith("data_sheets_schema/resources.py")
    data = tmp_path / "data/example.yaml"
    assert resources.repo_relative(data) == "data/example.yaml"
