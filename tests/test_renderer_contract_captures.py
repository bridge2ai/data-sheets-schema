"""Byte captures of what renderers 1-23 send, before #2924 deduplicates the contracts.

#2924 proposes a renderer that emits the v15-v17 contracts once. Every earlier
renderer must keep its bytes: frozen records replay their instruction, and
registrations pin it. These captures bind, for each accepted renderer, the
instruction both runtimes receive on the two existing fixtures, the per-phase
suffix the API path appends after the carried artifacts, and the assembly
digest. They were computed at origin/main cce0ba2ff, before any #2924 change.

The probe below records today's duplication: the v15, v16 and v17 texts occur
once per evidence phase contract, so three times in the joined contracts
section, and a fourth time in each API phase suffix. The dedup renderer is
expected to invert that probe for its own number only.
"""
from collections import Counter
from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

from data_sheets_schema import agentic_runtime, api_runner as api
from tests.test_claim_clarification_renderer import HISTORICAL
from tests.test_evidence_generation_gate import specification
from tests.test_source_metadata_renderer import fixture as metadata_fixture


RENDERERS = range(1, 24)
PHASES = ('audit', 'reconcile_full', 'report', 'report_regate')
RUNTIMES = {'api': 'Claude API (direct)', 'native': 'Claude Code'}
RUN_DATE = '2026-09-15'
ROOT_TOKEN = '<ROOT>'
CONTRACTS_HEADING = '## Required phase output contracts'
# The shared texts #2924 names, with the first renderer that appends each.
SHARED = {'ANONYMOUS_REMOVAL_CONTRACT_V15': 15, 'SOURCE_METADATA_CONTRACT_V16': 16,
          'CLAIM_CLARIFICATION_CONTRACT_V17': 17}

# A fixed installation. The real toolchain lists every shipped agent and
# command path, so a new file there or another interpreter would move native
# captures without any renderer change. The names are those shipped at capture.
PYTHON = '/opt/d4d/bin/python'
RESOURCES = (*agentic_runtime.SCHEMAS, *(f'.claude/commands/{name}.md' for name in (
    'README', 'd4d-add-mapping', 'd4d-agent', 'd4d-assistant', 'd4d-full-core',
    'd4d-input-deep-research', 'd4d-uniform-rules', 'd4d-webfetch')), *(
    f'.claude/agents/{name}.md' for name in (
        'd4d-description-reviewer', 'd4d-mapper', 'd4d-provenance-guard', 'd4d-review-record',
        'd4d-rocrate', 'd4d-rubric10-semantic', 'd4d-rubric10', 'd4d-rubric20-semantic',
        'd4d-rubric20', 'd4d-schema-expert', 'd4d-validator', 'schema-stats')))


def fixed_toolchain():
    return agentic_runtime.validate_toolchain(
        {'python': PYTHON, 'resources': {name: f'/opt/d4d/{name}' for name in RESOURCES}})


@pytest.fixture
def stable(monkeypatch):
    """Remove the inputs a capture must not depend on: the toolchain and the
    endpoint this process happens to be configured against."""
    monkeypatch.setattr(agentic_runtime, 'toolchain', fixed_toolchain)
    monkeypatch.setattr(api, 'provider_identity',
                        lambda: {'provider': None, 'base_url': None, 'key_env': None})
    monkeypatch.delenv('D4D_PROFILE', raising=False)


def fixtures(root: Path):
    """Both existing fixtures on both runtimes, rendered at a fixed date."""
    specs = {}
    for name, runtime in RUNTIMES.items():
        for kind, make in (('specification', lambda d, r: specification(d, r)),
                           ('metadata', lambda d, r: metadata_fixture(d, r)[0])):
            directory = root / f'{kind}_{name}'
            directory.mkdir(parents=True)
            specs[f'{kind}/{name}'] = replace(make(directory, runtime), run_date=RUN_DATE)
    return specs


def instructions(root: Path) -> dict[str, dict[int, str]]:
    """Each fixture's instruction per renderer, with the temporary root named."""
    texts = {}
    for key, spec in fixtures(root).items():
        texts[key] = {}
        for version in RENDERERS:
            text = replace(spec, render_version=version).instruction
            for spelling in sorted({str(root.resolve()), str(root)}, key=len, reverse=True):
                text = text.replace(spelling, ROOT_TOKEN)
            texts[key][version] = text
    return texts


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def captures(root: Path) -> dict:
    return {
        'instruction': {key: {v: sha256(text) for v, text in by_version.items()}
                        for key, by_version in instructions(root).items()},
        'phase': {phase: {v: sha256(api.phase_instruction(phase, v)) for v in RENDERERS}
                  for phase in PHASES},
        'assembly': {v: api.assembly_digest(v)['sha256'] for v in RENDERERS},
    }


def flatten(capture: dict) -> dict[tuple, str]:
    return {(family, key, version): digest
            for family, rows in capture.items() if family != 'assembly'
            for key, by_version in rows.items() for version, digest in by_version.items()} | {
        ('assembly', None, version): digest for version, digest in capture['assembly'].items()}


def contracts_section(text: str) -> str:
    start = text.find(CONTRACTS_HEADING)
    return text[start:] if start >= 0 else ''


def repeated_paragraphs(text: str, minimum: int = 200) -> dict[str, int]:
    """Paragraphs of at least `minimum` bytes that occur more than once.

    Paragraphs are compared stripped: the last copy of a contract ends the
    instruction and so lacks the separator the earlier copies carry.
    """
    counts = Counter(p.strip() for p in text.split('\n\n') if len(p.strip().encode('utf-8')) >= minimum)
    return {paragraph: n for paragraph, n in counts.items() if n > 1}


def shared_paragraphs(version: int, minimum: int = 200) -> set[str]:
    return {p.strip() for name, first in SHARED.items() if version >= first
            for p in getattr(api, name).split('\n\n') if len(p.strip().encode('utf-8')) >= minimum}


def heading(name: str) -> str:
    return getattr(api, name).splitlines()[0]


# Captured at origin/main cce0ba2ff with the fixed toolchain above.
INSTRUCTION = {
    'specification/api': {
        1: '6b72d38b185f411c3b90ea1645199813aba4141f8e71983712215af84f19df54',
        2: '1171836e7ec1e21b451c2b0bc34b4d42fed9929597c253a26bfe3ddcc7573365',
        3: 'b22e405a82a70ab78694b885ebca26786c97538a014032937418fe5ee8c565eb',
        4: '30f492b2caa208b4f6e4e9e2e8bd799123afc9b0537cd641776b87b9461733fe',
        5: '4a0457e8cf1454c9c0f15c5b199e7e14744ed0ed7ce2179a82782a81c205ecba',
        6: 'fbbcf52320eca16a632808e9626b79d1dc6a7ed6a81cf10adc526aa85614f17f',
        7: '551a3e99e294fc8a4980c759e7ae85cc55a3982ec915df4024e6bc6a5b0c48eb',
        8: '9a37c5b5a64ab0343e8b2d60d83f8c19b551aff304c6e6e993cc4900f05cbf8e',
        9: '55cb04f2360e177e4bd2893ca9c00e0e629922ae2c1e0de4b03f16c0e227bc78',
        10: '9f680b237e839c4d19e8e6f04b1c811d6bdd3bbb71af4582a503e1553640f757',
        11: '11900081d475540151d790d84c3491396eeda664c3429ffa07233ef9d0c145ee',
        12: '9832faae4d9b32b219adce517319495f2d384a96f1366f5c3343beee13689673',
        13: '2ce091cbe7272a350d494f3910bfbd731ccd718f6517914dde19bb7edaa38ec6',
        14: '6447eb34208e8fcf0e33c81fc9aa97f7f77212504f3157dda883eb6d5640b7f6',
        15: '9af71fee9248aba06869be9e5cb9265b30b76ee53e72f63810340217de353709',
        16: 'fbbb9cdc2e08b736b8b8f94f67c7226aeffaafbb1feb41f4559f61aa6797dd27',
        17: '52a328807c0d554849b983729d6868788e3cf6335bb304b0923c2933b1253e0c',
        18: 'eef155595d9e9411f08fe1d11888ef0580d0fff352c4ea5a0844354f48a8e394',
        19: '74fc2b37aff429dfa4ac1e6428db10f1450340f5b7795e9a5e2d7da40ecee43d',
        20: '95942a1ad0a61fdfe0a98bbd2b5e7cc9c983f30a3c37654c544eba71486dcf9a',
        21: 'cb38f52695415299cfb65d9bc0499c155accbf390f01375d2ba96da516575e82',
        22: 'b6b7cd7cdf2020bbda2f1fd8fe4d9eae7084d285744fee9006a22519b207e34a',
        23: 'd2f73e1d51df6330952df9fe479dc3dc299fedbe18b84efd1c40dcee0e8acbf0',
    },
    'metadata/api': {
        1: 'fd4058b4565403d3d58087d9e0ac51b0c2fed7474c084dfb8e85a471b433986e',
        2: 'e259eaa1dc73a0167e8e38571ba4e693e189fc6ee014414089a4e22016609ac8',
        3: 'cfe007bde97be047a3ea6b8574be46d77709705e064d440c4fc0aef5b76d60de',
        4: '3f7b19ba1605b877ec56487ebd880294948d521e9f45833c209073ea966bd049',
        5: '89cc3e7d602659f6134553537f7230be78a07f1e17c5f1ec6a8d6b85e97d06f7',
        6: 'd5f1297472cf8446ce1da664d82703751efe036247dbf5433409dd9d37f33cd2',
        7: 'eb77e07dde0d4243decd098d05820d5e771a0071b102eab275fe16db3e853dd9',
        8: '58f5a29877023a56e83f10c5d678940481743ecfcbb24f3b3516653e70c5056c',
        9: '518654fd7acd7a21fdd1603e1695d3d572afb2947d08064587ad113d1ff4e77f',
        10: 'aeb5a62495990311da3ce6d9b9d99603b6ea1e1952cfc2e6f2689b9e5c7acaa1',
        11: '0667101e57b7a06945dbe7f2d5de3430d53834e11957555402c394f9b8dc8b76',
        12: '453335ffc5966a547f2cf8e9c4e34967ea1b46317888428b8e05c59b46ee499f',
        13: '53051b8cff5aa0ed603040d10f4710e9a70ee3ec565d616473dded59097f85c9',
        14: '44752f83893e5e0f7db01dd34357e5012e275afbddfc5f57d438cd730f59a1a5',
        15: '9938c13511fef79f0f01d0d1d1fc496e415581de97cff966641889c0c86e2c49',
        16: '8367b86c58b618ef4e8bd2f33b3dc81b02a3b2a4329ab83a7294a6aed1e1a0d2',
        17: '406cee40ce6b85c3e08b1a70b9ea9625800b9555291d0247a445e2f694fc9569',
        18: '0341b375231dc840848824d4062afdb558cf783fc0235912b3912ad9406edf77',
        19: '3fd305c875ae90cdc9f715b725be38e243d631b0b4afbc7c1a0f447eceb4b808',
        20: 'c08164008a834a173c9e4505756a0c500b3d5079048a72e78b1772f7f0de2fb4',
        21: '330fdade6ee197b6ea043480036c7dc6d85fe5fbc67464bbf73785af93adaf46',
        22: 'f0eae7739a92f84e4c2db25148493777f79f94f36d798aed01b44c3d3a6043f8',
        23: '0047034a4ec5c05abe98abc2ad4d101f802ceafa3fe51f15826eb6b95fde140b',
    },
    'specification/native': {
        1: '0affe05e41e12f5002044490dbabbcd604d1e3d51b4eec4f75cdebb99742af5f',
        2: 'edd366f19048ae0e439edf1e334cf2defd5bf3323b96b642bedf9054ebce5e44',
        3: '269e62fb89f65e5dff3234a16d3affeaef967d0d005495e49cc88a8cdd06995b',
        4: '066a176e74a74667ffba41f17de00e143d1114658b0f6a8c9a4dc5cccbeb17fe',
        5: 'a3b7d559c74791623758956356649a6f2d7e7837e62237fdb4227ce3d3e09bf8',
        6: '8076d7c8554b1b572eb532d72cba454496468c7574e12400f8f70ff9321213e1',
        7: '6ee23ae395de755d40aaffb6d71cab51b3797cc2e43d5d25de3e01e54cffdd2d',
        8: 'bcf6f13413f31d8d1775a50c0752cbe0b5f124b252cc5ff17721969b0e56e6a9',
        9: 'f49bd2fc75c3b6dc01da2d4b253c2b39c3ea04fd90cb78d4e0b0de1df6596d37',
        10: '1fcd4522016378a8014087696fd759212bf98261d196eaf15d668346a817b03a',
        11: '68290dec4713b722154114d6a6c753f680df7673c64b615f0f803fb75ef90a15',
        12: 'f27055da913e1a91f84bf40be659eef4fa0aa66ce7e41db6fc3e6c8dda5500cf',
        13: '42593b6a31694918b002d561800760af23f8d5b6069a4a8bdb4aa7627ea50201',
        14: '513d6b0c4e40177741137701be6983db3c3ddd79c66462f2c2b0fa40794a5ebb',
        15: '4ca6fbb537025ea09d05c150b87fe464060dfacbfc3c829376080639e188b286',
        16: 'b3f8f33d93470ea680c18f6495c6c5404ff5bf45350a2b5bff6d069d8c0145d7',
        17: 'd0deed6a267fe3701a3d398f935df8bc484131e241c9613841c297518e2deaf4',
        18: '09a5ee3406de0702d82abe37173d0fdcc4ecfa04735b48ba36494da02b21152d',
        19: '2c9670370b79ae1def962b987c6448e652e15dc81fb10ceea58ed722892e4ec5',
        20: 'abb025628232ce0e539a172195330e6ffde889c6efe48344ee7a0063ac7996b5',
        21: 'fabac6a6b466a287d0ba1c9ef388375e08783787c816cbebbb90d56b931c23b2',
        22: '4d55d3f55bbde392782cbdc36a5d4b595f124df115ad75fb33ae23f35c713363',
        23: '20e8586d1ceed42ad76171d97e76029cafdabf6ea2887f49eb1588871ac91431',
    },
    'metadata/native': {
        1: '2c8e2ac848571d3d8aee4b46ae2dc3f9922295b269a3213e20688405857eba9d',
        2: '66da8e0e73c6c717d80df4eaab5cdeb4042d099808c37be257ccfda3f2fbd4fc',
        3: '9fc6acaca22fb177a12b9fde092bf566794a882cde3c3b3a833b5a41d1540315',
        4: 'd3518f436eb9c28d59b049adca80e12645901d2cb63262fab0ba4148fc9458c4',
        5: 'eb95ebb173597ffe229355624b2d1f08c73d334d7169cfb20b3e0b5620a64d3e',
        6: '134291789787f20c6e6fe7a288534440890ad8dd92baa9cd3b8f7726fe7e0d2e',
        7: '89d61359ce174d3215c51313577b73b8a4b7147237095d0d58812758a5d5e8c5',
        8: '0eebe2e22962002e0ba5aa589825415b21bb8428e2ab2d4f862b1b51a498acc3',
        9: '771b0af4f1c01ac14e4808fc70fd43a339343276111290fc4980f81a1b6a5ba0',
        10: '273ff706e9a5a3cfb20cd6af30c12b94f747a72ff6d1981508a046519864d8b2',
        11: '9ea773f190a5086ccf940eada57e08f55442e0d0dcb81a2b29ccb394da8137de',
        12: '5e4512479a1c2e398b4292b5081a0960f5b4d99a33304fd4afe5fc5cc297552c',
        13: '2202239739814c720db7419b9f2aa926fa6402b9eab02dc36c3f6d3ef3dcc8fb',
        14: 'b9c8b967e9eaa69a5a4f747eb354386c7a88d99a06c74b7fee6632cb984684b2',
        15: 'cf968a7c7eec9b469f3f77b1d6f3d5662bc03ce7931579ba94947db25383de9c',
        16: '639d144282150ae558bac2cac6f75236a907bc4a3b9c429a3f182d8e4beb7893',
        17: 'b28243e188046ce65d1ac69e16390c449af94b33d6af85eab2db442fbda0f85c',
        18: '455599ba550b4c1787354e1e7412e41421ceaa79509f76865f59c5f2e8e10821',
        19: 'da2ff86183cdc05a40bca8e448dfcd945f2b23aa0b0abf31ab643a8965936f2c',
        20: '7ae93e5fedd0f4f3c5b6bb761704a31f23b8cd00dce694d59cec31ff943a3373',
        21: 'cbb006623bcf39a24517a4d8630453f8b2f49c953d25e2679995db9c83118550',
        22: 'e0c77ee9103180be1d0961cb8523fe5d00109061ef46c660690a6551372c18ce',
        23: '69f9856ae29d04ab21056a89e9d564bf569839cd6fd7dc8cf8fd355edea64fd4',
    },
}
PHASE = {
    'audit': {
        1: '91296b20b628a7e9b202320c93d551f22cdd17e8382bad685e9d3d4033b239ee',
        2: '91296b20b628a7e9b202320c93d551f22cdd17e8382bad685e9d3d4033b239ee',
        3: '91296b20b628a7e9b202320c93d551f22cdd17e8382bad685e9d3d4033b239ee',
        4: '91296b20b628a7e9b202320c93d551f22cdd17e8382bad685e9d3d4033b239ee',
        5: '91296b20b628a7e9b202320c93d551f22cdd17e8382bad685e9d3d4033b239ee',
        6: '91296b20b628a7e9b202320c93d551f22cdd17e8382bad685e9d3d4033b239ee',
        7: '91296b20b628a7e9b202320c93d551f22cdd17e8382bad685e9d3d4033b239ee',
        8: '91296b20b628a7e9b202320c93d551f22cdd17e8382bad685e9d3d4033b239ee',
        9: '91296b20b628a7e9b202320c93d551f22cdd17e8382bad685e9d3d4033b239ee',
        10: 'a8be7aa70644ba14aad2cd0d921eb39c3f8f97bcbc33918a74a5d2185e755023',
        11: 'cdb4084434233b5af6c8ac4f441cbcb52e4f75d4f140f2f1e75d6a1a305e80c4',
        12: '9577d1fbe2ce90ec60ee0983fb46685160a5e0f57c7ea0b66918b10294b98177',
        13: '9577d1fbe2ce90ec60ee0983fb46685160a5e0f57c7ea0b66918b10294b98177',
        14: 'fa90fe026fb3439b84a30ce92c58472c337ca78513ae2baf634da9e08e3d6bc3',
        15: 'dc71062186358dc66f0b05c5a6959275cbbebe9f47931860f09977c1b3170962',
        16: '993e7751575b99f90875e0749cb94fc1faf95140c4cbef96af5ccd8e9e2065ce',
        17: '0cbb1f23f62babd4c8e38f1ff4006fde899a3195bff0711d3ab8e6ecad510e62',
        18: '0829f97bb7a47a8b15c9e16c0e2f1ff49f01ad9ab882a78e9ea59c6e80c3acbd',
        19: '78b7c10a39ab489a99ca50336097e1852a2347c27121a7eaf79a93c6a3ade04b',
        20: '2cd29fb6ee202aa12283e0368054bc56042c5facbb7132862df59ef3028a5111',
        21: '2cd29fb6ee202aa12283e0368054bc56042c5facbb7132862df59ef3028a5111',
        22: '2cd29fb6ee202aa12283e0368054bc56042c5facbb7132862df59ef3028a5111',
        23: '2cd29fb6ee202aa12283e0368054bc56042c5facbb7132862df59ef3028a5111',
    },
    'reconcile_full': {
        1: 'c858f9cd91bdafdb54c0e45d0130e07b62af0a48ba19fee7b7231e45c6e7bdbf',
        2: 'c858f9cd91bdafdb54c0e45d0130e07b62af0a48ba19fee7b7231e45c6e7bdbf',
        3: 'c858f9cd91bdafdb54c0e45d0130e07b62af0a48ba19fee7b7231e45c6e7bdbf',
        4: 'c858f9cd91bdafdb54c0e45d0130e07b62af0a48ba19fee7b7231e45c6e7bdbf',
        5: 'c858f9cd91bdafdb54c0e45d0130e07b62af0a48ba19fee7b7231e45c6e7bdbf',
        6: 'c858f9cd91bdafdb54c0e45d0130e07b62af0a48ba19fee7b7231e45c6e7bdbf',
        7: 'c858f9cd91bdafdb54c0e45d0130e07b62af0a48ba19fee7b7231e45c6e7bdbf',
        8: 'c858f9cd91bdafdb54c0e45d0130e07b62af0a48ba19fee7b7231e45c6e7bdbf',
        9: 'c858f9cd91bdafdb54c0e45d0130e07b62af0a48ba19fee7b7231e45c6e7bdbf',
        10: '0f9634381c0253fd68f8a1d35facb44d0a696b3ee782dc1edcd8f23e4630b5ba',
        11: 'd21d4bed0449758b763f401632656558fddaebfca0f55dffeb86377f582d4dab',
        12: '944e150b7d30b60d7eff3ec9b72e68a2bf655fdc1713f579390262e020cc20ef',
        13: '944e150b7d30b60d7eff3ec9b72e68a2bf655fdc1713f579390262e020cc20ef',
        14: '944e150b7d30b60d7eff3ec9b72e68a2bf655fdc1713f579390262e020cc20ef',
        15: '712964976c01d9967a6562d4674b19b2757f2c94950f075be2dfca8ade449b41',
        16: '83345e6c6ffc74ab472d8faf77858b2446b82e1053b2825b6a2d9d4f6919e32d',
        17: 'fca2676c269212a162a5f28383e70bd11335a51f9432584eb687e3f6918399fb',
        18: '6ba9688d0e6ad180e6e7b972d9adbbddc36267f2396e5f394b2d7ffdbfd18c36',
        19: '6ba9688d0e6ad180e6e7b972d9adbbddc36267f2396e5f394b2d7ffdbfd18c36',
        20: 'd9519b419be5cea42b59e335c1efc68a4dc022fd664d651b036ee55c5a6e9958',
        21: 'd9519b419be5cea42b59e335c1efc68a4dc022fd664d651b036ee55c5a6e9958',
        22: 'd9519b419be5cea42b59e335c1efc68a4dc022fd664d651b036ee55c5a6e9958',
        23: 'd9519b419be5cea42b59e335c1efc68a4dc022fd664d651b036ee55c5a6e9958',
    },
    'report': {
        1: 'eb68d15ccad8f8e6fed610140fc899293501f61068cbccf3eb4fac3e3e5a796b',
        2: 'eb68d15ccad8f8e6fed610140fc899293501f61068cbccf3eb4fac3e3e5a796b',
        3: 'eb68d15ccad8f8e6fed610140fc899293501f61068cbccf3eb4fac3e3e5a796b',
        4: 'eb68d15ccad8f8e6fed610140fc899293501f61068cbccf3eb4fac3e3e5a796b',
        5: 'eb68d15ccad8f8e6fed610140fc899293501f61068cbccf3eb4fac3e3e5a796b',
        6: 'eb68d15ccad8f8e6fed610140fc899293501f61068cbccf3eb4fac3e3e5a796b',
        7: 'eb68d15ccad8f8e6fed610140fc899293501f61068cbccf3eb4fac3e3e5a796b',
        8: 'eb68d15ccad8f8e6fed610140fc899293501f61068cbccf3eb4fac3e3e5a796b',
        9: 'eb68d15ccad8f8e6fed610140fc899293501f61068cbccf3eb4fac3e3e5a796b',
        10: 'd986dca9286b4d4cbe9865cf869d623df5d017a252ec3d45c0069520a7488646',
        11: '64317897ce2c0b07ba5ca146314bdc42f9704a32fa843a9a04186b8bfb420feb',
        12: 'ab64a5883c2b40d207aae6761aa25b4b5dc3172e6813d9fa958aefde8aea805c',
        13: 'ab64a5883c2b40d207aae6761aa25b4b5dc3172e6813d9fa958aefde8aea805c',
        14: 'ab64a5883c2b40d207aae6761aa25b4b5dc3172e6813d9fa958aefde8aea805c',
        15: '07733043b41ca1d17cd8b084d1b7d28e49277e8343182b36b922b272072c3718',
        16: '05dc5512df6ccdf384b6dfb423f57abe7d9d462f92a1763e0b4945e7b1a3d053',
        17: '59501ff4eaa6624f0d4c3af50de2dd6cb8b440462eac0e0a59b2f4e76a30b027',
        18: 'a28efc00eb1fe68bdf1361eabb51b4390c0cebe1c72ed6dbf15696e042e58094',
        19: 'a28efc00eb1fe68bdf1361eabb51b4390c0cebe1c72ed6dbf15696e042e58094',
        20: '96aa6c6f0940ffba049460ed34451014f4c34829b5e551efb0494fb100400a2a',
        21: '96aa6c6f0940ffba049460ed34451014f4c34829b5e551efb0494fb100400a2a',
        22: '96aa6c6f0940ffba049460ed34451014f4c34829b5e551efb0494fb100400a2a',
        23: '96aa6c6f0940ffba049460ed34451014f4c34829b5e551efb0494fb100400a2a',
    },
    'report_regate': {
        1: '24bc01cf98c075d80f20569c610918e97c124201f17734d49e485d77efa2bb6f',
        2: '24bc01cf98c075d80f20569c610918e97c124201f17734d49e485d77efa2bb6f',
        3: '24bc01cf98c075d80f20569c610918e97c124201f17734d49e485d77efa2bb6f',
        4: '24bc01cf98c075d80f20569c610918e97c124201f17734d49e485d77efa2bb6f',
        5: '24bc01cf98c075d80f20569c610918e97c124201f17734d49e485d77efa2bb6f',
        6: '24bc01cf98c075d80f20569c610918e97c124201f17734d49e485d77efa2bb6f',
        7: '24bc01cf98c075d80f20569c610918e97c124201f17734d49e485d77efa2bb6f',
        8: '24bc01cf98c075d80f20569c610918e97c124201f17734d49e485d77efa2bb6f',
        9: '24bc01cf98c075d80f20569c610918e97c124201f17734d49e485d77efa2bb6f',
        10: 'ad1bffa84d865a2f2654cb41642a5c5a0f8a0189822cc64f3841512657736289',
        11: '5a807924d6e362cb4bb2801dc4fdb2889d4361df76e437e8ae767d6f1479e985',
        12: 'a26caa64b89aedab395acfff48671239e4e5c25ace8f3229a927a3f551c1e41a',
        13: 'a26caa64b89aedab395acfff48671239e4e5c25ace8f3229a927a3f551c1e41a',
        14: 'a26caa64b89aedab395acfff48671239e4e5c25ace8f3229a927a3f551c1e41a',
        15: 'f7624c6125ac69b6c4f4475e6f158f8088bce24cac35cf54f20ab70d14168878',
        16: '83fa1fdeb1010c32bfa18c1288cde2d055f52a213a3119d097623b2b8b32976c',
        17: '23ea8896656eb902a8b5a60ee98092ed48d329434efdf7f95bd6d91203c7d079',
        18: 'b840b8b37eb0d3722b77e1f1f70936d3222241ad296b2ea7344feb7349b073fe',
        19: 'b840b8b37eb0d3722b77e1f1f70936d3222241ad296b2ea7344feb7349b073fe',
        20: 'ffe24d4306fab15c0c6e766c9bea84591f44896fc8ef34a9184d46bb7db91cff',
        21: 'ffe24d4306fab15c0c6e766c9bea84591f44896fc8ef34a9184d46bb7db91cff',
        22: 'ffe24d4306fab15c0c6e766c9bea84591f44896fc8ef34a9184d46bb7db91cff',
        23: 'ffe24d4306fab15c0c6e766c9bea84591f44896fc8ef34a9184d46bb7db91cff',
    },
}
ASSEMBLY = {
    1: '39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3',
    2: '39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3',
    3: '39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3',
    4: '39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3',
    5: '39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3',
    6: '39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3',
    7: '39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3',
    8: '39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3',
    9: '39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3',
    10: 'efd42e290b8fa347d663fd7953d896d45a12827bca0049df64d9b74dd48c4eba',
    11: 'b7e2f4dcd2db81121c03204f1ce1171682f5e1894b7164f9e37a4d2e6810578d',
    12: '1e3b4d5df240f67f9aae814e4494017b79804ecce06a16504eb0b084f5082a4a',
    13: 'adc8d2982d744dced2505134e18fde58a1b97ea079b40df7cd7e146ffeb549b5',
    14: 'd5f55d9ff58bbcbf94e70a4528e13bd0b2815a9a87e1d8fd0e6ab7a912bdf924',
    15: '79d0d4a45d908a0f699bf15af53c24854b16c00bce4a94596a5687a584d01097',
    16: 'ea4117e600ebeb3a0bbd940c2c7d9047e5925f68faac2d876a48f6a8e87127d1',
    17: '083b90de0c82ea464686e6f9d46e6cefb09cce7c98bb55aab2d6054037a4045a',
    18: '8994bb0d648a354c9d14fc81761a2264f74922ededa9ec4b51fb99072f2f3002',
    19: '4bd4a55c1e5c8473ec0ffae423a6708fe8bff75da17980935e3e5752e06072e1',
    20: 'd6005d48d13dc099d3d30179d88948e4b6284541ba5e414d1e310fc5bed59e14',
    21: 'd6005d48d13dc099d3d30179d88948e4b6284541ba5e414d1e310fc5bed59e14',
    22: 'd6005d48d13dc099d3d30179d88948e4b6284541ba5e414d1e310fc5bed59e14',
    23: 'd6005d48d13dc099d3d30179d88948e4b6284541ba5e414d1e310fc5bed59e14',
}
CAPTURED = {'instruction': INSTRUCTION, 'phase': PHASE, 'assembly': ASSEMBLY}


def test_every_accepted_renderer_is_captured(tmp_path):
    spec = specification(tmp_path)
    accepted = []
    for version in range(0, 40):
        try:
            replace(spec, render_version=version)
        except ValueError:
            continue
        accepted.append(version)
    # A new renderer must add its captures here; the old ones stay as they are.
    assert accepted == list(RENDERERS)
    assert set(ASSEMBLY) == set(RENDERERS)
    assert {key: set(rows) for key, rows in INSTRUCTION.items()} == {
        f'{kind}/{name}': set(RENDERERS) for kind in ('specification', 'metadata') for name in RUNTIMES}
    assert {phase: set(rows) for phase, rows in PHASE.items()} == {phase: set(RENDERERS) for phase in PHASES}


def test_captures_match_the_rendered_bytes(tmp_path, stable):
    assert captures(tmp_path) == CAPTURED


def test_assembly_captures_agree_with_the_existing_historical_pins():
    assert {v: ASSEMBLY[v] for v in HISTORICAL} == HISTORICAL


def test_a_v17_mutation_moves_captures_for_renderers_17_to_23_only(tmp_path, stable, monkeypatch):
    before = flatten(captures(tmp_path / 'before'))
    monkeypatch.setattr(api, 'CLAIM_CLARIFICATION_CONTRACT_V17',
                        api.CLAIM_CLARIFICATION_CONTRACT_V17 + 'Changed.\n')
    after = flatten(captures(tmp_path / 'after'))
    assert before.keys() == after.keys()
    moved = {key for key in before if before[key] != after[key]}
    assert moved == {key for key in before if key[2] >= 17}


def test_probe_shared_contracts_occur_three_times_in_the_joined_section(tmp_path, stable):
    for key, by_version in instructions(tmp_path).items():
        for version, text in by_version.items():
            section = contracts_section(text)
            for name, first in SHARED.items():
                assert text.count(heading(name)) == section.count(heading(name)) == (
                    3 if version >= first else 0), (key, version, name)
            repeated = repeated_paragraphs(section)
            # Every repeated long paragraph is shared contract text, three times.
            assert set(repeated) == shared_paragraphs(version), (key, version)
            assert set(repeated.values()) <= {3}, (key, version)


def test_probe_each_api_phase_suffix_carries_one_more_copy():
    for phase in PHASES:
        for version in RENDERERS:
            text = api.phase_instruction(phase, version)
            for name, first in SHARED.items():
                assert text.count(heading(name)) == (1 if version >= first else 0), (phase, version, name)
                assert (getattr(api, name) in text) == (version >= first), (phase, version, name)


def test_probe_measures_the_duplicated_bytes_at_renderer_17(tmp_path, stable):
    text = instructions(tmp_path)['specification/native'][17]
    section = contracts_section(text)
    redundant = sum(len(p.encode('utf-8')) * (n - 1) for p, n in repeated_paragraphs(section).items())
    # The issue's 21,873-byte section. Its 8,854 redundant bytes compared
    # unstripped paragraphs, which misses the final v17 paragraph's last copy
    # (696 B); stripped, the two redundant copies are 2 x 4,775 B.
    assert len(section.encode('utf-8')) == 21873
    assert redundant == 9550
