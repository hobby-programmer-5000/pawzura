[English](../en/RELEASE-v0.3.0.md) | [한국어](../ko/RELEASE-v0.3.0.md) · [Documentation](../README.md)

# 0.3.0 — artwork hands, feet and reactions

Artwork now supports independently moving arm/hand and foot cutouts, with walking, waving, hopping and cheering poses. Hover pauses walking and greets the cursor; successive clicks cycle wave/hop/cheer. Double-click or right-click opens settings. A periodic idle wave adds variety. Guardian bites retain precedence and their existing closing protections.

New artwork preparation adds an optional Apache-2.0 ViTPose CPU joint helper (~350 MB weights) and SciPy (BSD-3-Clause). Generation proposes four editable regions; the default example now explicitly requests visible hands/feet. Existing images need no regeneration: **Character → Edit hand/foot motion… → Prepare helper → Estimate joints automatically → Use motion settings → Save settings**. Manual adjustment works without the helper. Preparation reuses the isolated runtime; first-time runtime downloads are larger than 350 MB.

This is 2D cutout animation, with no continuous model inference while walking. Incorrect joints, hidden limbs and sleeve seams can require manual corrections. The original PNG stays intact; disable independent motion to restore the whole-picture fallback. The editor provides four-pose previews and localized progress/errors. See [motion controls and corrections](ARTWORK-MOTION.md), [model/license guide](CREATIVE-ART.md) and [validation](VALIDATION.md).

The 0.2.2 long-description review fix is included. Extract the complete new ZIP into a new folder, quit the old running Pawzura yourself and start the new EXE. Existing local settings/artwork are reused; personal lists and generated artwork are not distributed.
