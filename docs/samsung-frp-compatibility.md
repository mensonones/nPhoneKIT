# Samsung FRP compatibility matrix

This matrix records claims that are safe to make from the current project
inventory. It is not a guarantee that a method will work on a particular
phone. Only test devices that are owned by, or explicitly authorised by, the
person running the test.

| Patch band | Project method | Status | Notes |
| --- | --- | --- | --- |
| Before 2022-08 | `sam_pre_2022` | Candidate | Legacy flow; exact model/build still matters. |
| 2022-08 through 2022-12 | `sam_2022_23` | Candidate | The UI historically called this 2022/2023; no complete model matrix exists. |
| 2023 | Any Samsung FRP flow | Not validated | Do not infer support from the 2022/2023 label. |
| 2024 | `sam_2024` | Limited candidate | Existing documentation only claims some U.S. models. |
| 2025–2026 | Any Samsung FRP flow | Not validated | No project evidence currently covers these patch bands. |
| Unknown/missing patch level | Any flow | Unknown | Collect firmware, model, CSC/region and patch level first. |

## Required test record

For each authorised test, record:

`model | Android version | security patch | build/software version | CSC/region | method | result | evidence`

A result should not be promoted from “candidate” to “confirmed” until it has
been reproduced on the same model/build and the evidence is retained. A
failure should be recorded as a failure for that exact combination, not
generalised to every device in the same product family.

## Official update references

- [Samsung Mobile Security Updates](https://security.samsungmobile.com/securityUpdate.smsb)
- [Samsung Mobile Security device/update scope](https://security.samsungmobile.com/workScope.smsb)
- [Android Security Bulletins](https://source.android.com/docs/security/bulletin/asb-overview)

Samsung and Android publish security fixes by release and device scope; those
bulletins do not constitute a compatibility guarantee for this project.
