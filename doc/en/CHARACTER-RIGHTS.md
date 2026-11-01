[English](../en/CHARACTER-RIGHTS.md) | [한국어](../ko/CHARACTER-RIGHTS.md) · [Documentation](../README.md)

# Character rights and provenance

The purpose is to document the existing character's origin and the maintainer's objection to someone claiming an exclusive registration and excluding its original users. Branding or a trademark application is not currently planned. The [character rights notice](../../CHARACTER-POLICY.md) accompanies the source and future Windows packages.

## What the licensing says

- The source, renderer and existing MIT permissions remain [MIT](../../LICENSE). Users may run, modify and redistribute the software, including commercially, subject to MIT's notice requirement. Copying it does not transfer the original copyright.
- The maintainer gives no separate authorization here for another party to register the existing artwork as its exclusive trademark or registered design. This does not assert that the maintainer already has registered or enforceable trademark/design rights.
- The anti-appropriation request expresses the maintainer's position. It is not a new condition imposed on MIT recipients, an automatic contract with every reader, or a guarantee that a stranger cannot file.
- A derivative's new protectable contributions can have their own rights. They do not make the modifier the original creator of the pre-existing work. No monopoly is claimed over generic shapes, animal features, colors or an independently created character.

Adding a bespoke “no registration” condition to MIT would change its terms. This project does not relabel such a modified license as MIT or attempt to revoke earlier grants. No CC license or custom character license has been applied to replace the existing permissions.

## Recorded origin

| Item | Repository record |
| --- | --- |
| Product direction and requirements | hobby-programmer-5000; see [roles](CONTRIBUTORS.md) |
| Drawing implementation | AI-assisted QPainter geometry written through ChatGPT/Codex, not a commissioned human-drawn asset |
| First recorded renderer | Commit `e954e5947e0b361aa3004f6d8ad62ee4b40043d7`, recorded 2026-11-02 03:50:46 +09:00 |
| Source baseline for this notice | Commit `bd2c0734db4a8a4f1aa90571f12c5c9ebdb44c9a` |
| Renderer at that baseline | [pawzura/pet.py](../../pawzura/pet.py), `draw_character` |
| Default appearance at that baseline | [pawzura/config.py](../../pawzura/config.py): body `#b8a4ed`, accent `#f9ce80`, rabbit ears, scarf; seed varies |
| Other appearances / motion | Bounded random or optional Qwen appearance values; procedural motion, no imported mascot/sprite/motion-model assets |

SHA-256 below is calculated over the exact Git blob bytes at the baseline commit, not a platform's line-ending-converted working copy. Later changes need their own version records; these identify a historical baseline.

| Baseline file | SHA-256 |
| --- | --- |
| `pawzura/pet.py` | `b22db9533656cee5716ca164da3ed3ef7111e440aff9df6b569cdd037628ae41` |
| `pawzura/config.py` | `1c72211ede187ef81a0dfc789d84acd1de1b59e5102c01f39921c175435f70cd` |

Git dates and hashes help identify a version. They are not a government timestamp, proof of exclusive authorship, trademark registration, or proof of public recognition. A private repository is not evidence of public use merely because it has commits. Keep the original repository and dated distribution records; no personal account lists or local settings belong in this record.

## Limits relevant to the concern

Copyright licensing and trademark registration address different rights. Even standard public licenses distinguish them; see [Creative Commons' official explanation](https://creativecommons.org/faq/#can-i-offer-material-under-a-cc-license-that-has-my-trademark-on-it-without-also-licensing-or-affecting-rights-in-the-trademark). That explanation does not apply a CC license to this project.

Someone filing a trademark does not thereby receive copyright ownership of the drawing. Whether a filing can be opposed, invalidated or asserted depends on the jurisdiction, goods/services, prior rights and evidence. The notice cannot make an IP office reject applications automatically. [Official Korean trademark explanation](https://www.kipo.go.kr/ko/kpoContentView.do?menuCd=SCD0200242).

AI assistance does not justify claiming exclusive copyright in every generated visual. Human creative contribution and applicable law need assessment. This record states the actual roles instead of claiming that a human hand-drew the character. [Official Korean AI copyright guidance](https://www.kipo.go.kr/ko/kpoBultnDetail.do?aprchId=BUT0000029&menuCd=SCD0200618&ntatcSeq=21075&sysCd=SCD02).

If an actual conflicting filing appears, retain its application details and the original source/distribution evidence and obtain jurisdiction-specific advice about the response deadline and available grounds. No registration, opposition or public disclosure is performed by adding this document.
