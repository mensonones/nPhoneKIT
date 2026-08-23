<div align="center" markdown="1">
<h1>nPhoneKIT</h1>

<img src="images/nphonekit-screenshot.png" height=700px width=700px>

<u>**Safe, free, open-source.**</u>

[![Built with Python](https://img.shields.io/badge/Built%20with-Python-Purple)](https://python.org)
[![Mastodon](https://img.shields.io/badge/-Mastodon-%232B90D9?logo=mastodon&logoColor=white)](https://mastodon.social/@nlckysolutions)
[![Matrix](https://img.shields.io/badge/Matrix-FFF?logo=matrix&logoColor=000)](https://matrix.to/#/#nphonekit:matrix.org)

A fully open-source, community-powered toolbox for Android devices — a transparent
alternative to closed-source unlock tools that hide what they do to your phone.

**Need to use nPhoneKIT programmatically in Python scripts? See [nPhoneCLI](https://github.com/nlckysolutions/nPhoneCLI).**

</div>

---

> **Like the project?** Star the repo — it's the simplest way to support development and get updates.

> [!IMPORTANT]
> Recommended reading before you start: [this post](https://nlcky.solutions/?p=35), for both new and existing users.

## Table of Contents

- [About](#about)
- [Features](#features)
- [Installation](#installation)
  - [Windows](#windows)
  - [Linux (Debian-based)](#linux-debian-based)
  - [Linux (Arch-based)](#linux-arch-based)
  - [MediaTek features on Linux](#mediatek-features-on-linux)
- [Important Information](#important-information)
- [Known Bugs](#known-bugs)
- [Development & Contributing](#development--contributing)
- [Privacy](#privacy)
- [Credits](#credits)
- [Legal](#legal)

---

## About

**nPhoneKIT** replaces certain closed-source tools that *hide* what they are doing
to your phone. Unlike some alternatives — which are obfuscated and often flagged by
antivirus scanners — nPhoneKIT is:

- 100% open Python code.
- Transparent: it shows you the exact commands it runs.
- Capable: it does most of what other tools can do anyway.

There is no "magic click" — just real commands and real transparency.

> [!IMPORTANT]
> Have an idea for a feature, or an open-source unlock you'd like to see? Open an
> issue for feature requests or bugs. Most submitted requests and bugs are targeted
> for nPhoneKIT v2. To help speed up releases, fill out the form shown after an
> unlock (when Contribution Suggestions is enabled).

---

## Features

### Samsung
- FRP compatibility is documented in [the compatibility matrix](docs/samsung-frp-compatibility.md).
- Candidate support for some pre-Aug 2022 and Aug–Dec 2022 patch bands.
- Limited candidate support for some U.S. 2024 devices.
- 2023 and 2025–2026 patches are not validated.
- Get version / firmware info on all Samsung devices.
- Reboot Samsung devices (normal or into Download Mode).
- Open the hidden WLANTEST menu on all Samsung devices.
- IMEI check.
- Remove bloatware.

### Motorola
- Experimental FRP unlock.

### LG
- Legacy screen unlock (pre-G5).

### MediaTek
- MTKClient (by [@bkerler](https://github.com/bkerler/mtkclient)).

### Generic Android
- Reboot.

---

## Installation

nPhoneKIT is tested on Python 3.10–3.12.

### Windows

> [!TIP]
> Prefer video? Follow the [easy installation walkthrough](https://youtu.be/hSK-dW2cTaY).

<details>
<summary>Step-by-step install guide</summary>

1. Download [Zadig](https://zadig.akeo.ie/) and install the WinUSB and libusb-win drivers.
2. Using a Samsung device? Also install the [Samsung USB drivers](https://developer.samsung.com/android-usb-driver).
3. Install [Python and Pip](https://www.python.org/downloads/windows) if you don't have them.
4. Go to the latest release and download the source code as a ZIP.
5. Extract the ZIP, open Command Prompt **as Administrator**, and `cd` into the source directory.
6. Install dependencies:
   ```
   pip install -r requirements.txt && pip install -r ./deps/mtkclient/requirements.txt
   ```
7. Launch nPhoneKIT (run this from the source folder, as Administrator, each time):
   ```
   python main.py
   ```

</details>

### Linux (Debian-based)

> [!TIP]
> **One command (Debian/Ubuntu):** from the source folder, run
> ```bash
> ./run.sh
> ```
> It installs every dependency (Python packages, the Qt system libraries, and adb),
> adds you to the `dialout` serial group if needed and launches with it active
> (**no reboot required**), then starts nPhoneKIT. Already set up? Use
> `./run.sh --no-install`. The manual steps below do the same thing by hand.

> [!TIP]
> Prefer video? Follow the [easy installation walkthrough](https://www.youtube.com/watch?v=lv1ZMkxWEVo).

<details>
<summary>Manual install guide</summary>

1. Go to the latest release and download the source code as a ZIP.
2. Extract the ZIP, open a terminal, and `cd` into the source directory.
3. Install dependencies:
   ```
   sudo apt install python3 python3-tk python3-serial python3-requests python3-pyqt5 adb
   ```
4. Launch nPhoneKIT (run this from the source folder each time):
   ```
   python3 main.py
   ```

</details>

### Linux (Arch-based)

> [!TIP]
> Prefer video? Follow the [easy installation walkthrough](https://youtu.be/2JWpJUhficA).

<details>
<summary>Manual install guide</summary>

1. Get the source, either by downloading the latest release ZIP or cloning the repo:
   ```
   git clone https://github.com/nlckysolutions/nPhoneKIT.git
   ```
2. `cd` into the source directory (`cd nPhoneKIT`).
3. Install dependencies:
   ```
   sudo pacman -Syu python3 tk python-pyserial python-requests pyqt5 android-tools
   ```
4. Launch nPhoneKIT (run this from the source folder each time, with `sudo`):
   ```
   sudo python3 main.py
   ```

</details>

### MediaTek features on Linux

MTKClient features require a dedicated virtual environment. From the source folder
(the one containing `main.py`), run:

```
sudo python3 -m venv ./deps/venv
sudo bash -c 'source ./deps/venv/bin/activate && pip install -r ./deps/mtkclient/requirements.txt'
```

> [!IMPORTANT]
> These commands are **required** on Linux to enable any MTKClient features.
> Without them, MTKClient will not open from nPhoneKIT.

---

## Important Information

Please read before using:

- Motorola FRP fastboot unlock is **experimental** and is not likely to work.
- nPhoneKIT uses the same unlock methods as many other free tools, but is open-source.
- nPhoneKIT will never ask for payment and will never show ads.
- nPhoneKIT was built mostly for education — by open-sourcing common unlock methods —
  but is also reasonably reliable.
- nPhoneKIT is fully FOSS. Donations are appreciated but never required, and your
  GitHub username can be listed here if you'd like.
- nPhoneKIT is meant to be used responsibly, by the rightful owners of their own phones.

---

## Known Bugs

As of v1.6.3:

- Motorola FRP is not working for most devices.

> [!IMPORTANT]
> Found a **new** bug? Open a GitHub issue. It helps get the bug fixed and makes
> nPhoneKIT better for everyone.

---

## Development & Contributing

nPhoneKIT is organized as `main.py` (the application shell) plus focused
`nphonekit_*` modules, covered by a unit-test suite that runs in CI on
Python 3.10 and 3.12. See [ARCHITECTURE.md](ARCHITECTURE.md) for a module map.

Set up a dev environment and run the same checks CI does:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
ruff check .        # lint
pytest              # tests
```

> [!NOTE]
> On Linux, PyQt5 installed from **pip** (as above) does not pull in the Qt
> "xcb" platform system libraries, so the GUI fails to start with
> `Could not load the Qt platform plugin "xcb"`. Install them once with:
> ```bash
> ./scripts/install-linux-deps.sh
> ```
> This is **not** needed if you install PyQt5 from your distro
> (`python3-pyqt5` / `pyqt5`), which already depends on them — that's the case
> for the apt/pacman install steps above.

- **Bugs / feature requests:** open a GitHub issue.
- **Security issues:** see [SECURITY.md](.github/SECURITY.md) — please report privately.

---

## Privacy

- **Automatic telemetry is disabled in this build. nPhoneKIT does not contact
  external servers on its own.**
- Historically a "Success Checks" feature reported (anonymized, hashed) whether an
  action worked on a phone model. It is now turned off at the source
  (`TELEMETRY_ENABLED = False` in `main.py`) and can only be re-enabled by editing the code.
- Automatic update checks are also **off by default**.
- The only network access is **user-initiated**: submitting a feature/bug report,
  opening the IMEI-check page in your browser, or an opt-in update check.

---

## Credits

- **MediaTek features work only through MTKClient, which is in the DEPS folder.**
  Sourced from https://github.com/bkerler/mtkclient. MTKClient is provided by
  bkerler and is **not** owned or created by nPhoneKIT in any way.
- **IMEI checking works by opening a new tab of www.imei.info** so you can check
  your IMEI yourself.

### Thank you to our contributors!

- @lggcs
- @Radulepy
- @TimelessFez
- Erkan
- Connor
- Sino975
- DMZP
- Henintsoa
- mahfoudh
- lhteufel
- sassysky

---

## Legal

<sub>nPhoneKIT is a tool built entirely from original Python code. It does not include, link to, or distribute any copyrighted firmware, exploits, or proprietary binaries. Any similarity in function to other tools is the result of using standard public command sets (e.g. ADB, AT). This project is not affiliated with or endorsed by Samsung, LG, Google, or other companies. Trademarks used for descriptive purposes only.</sub>
