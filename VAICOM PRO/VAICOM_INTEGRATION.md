# VAICOM PRO Integration

VAICOM PRO is a VoiceAttack plugin used to integrate with Digital Combat Simulator (DCS) for communicating with AI units without needing to use the F10 comms menus.

These instructions detail how to integrate Whisper server with VoiceAttack and VAICOM PRO.

**WARNING:** These instructions are a work in progress. WhisperAttack is in beta and things are subject to change.

The VAICOM PRO manual can be found on the VAICOM PRO Community Discord server.

An example VoiceAttack profile `WhisperAttack for VAICOM PRO.vap` is available here which is based on the default VAICOM PRO one, with updates made for Whisper support. This can be imported into VoiceAttack and used for your purposes.

## 1. VAICOM PRO VSPX Speech Processing Mode

Within the VAICOM configuration the speech processing engine must be set to VSPX in the preferences. This is due to VoiceAttack not supporting wildcard (`*`)
characters when matching "When I say" commands when it is executed by the Whisper server. The VAICOM PRO VSPX processing engine, and the exported
key words from its database when run in this mode, use official supported "When I say" VoiceAttack syntax that is required for Whisper.

## 1. VAICOM PRO keywords database

The VAICOM PRO configuration contains an editor that can be used to add aliases for commands. WhisperAttack converts textual numbers to numerical values, e.g. "two" is 2. Because of this aliases will need to be added for keywords that contain textual numbers. For example, your wingman has the existing aliases of "two", "winger", and "bozo". You will need to add another alias for this with a value of `1`. This will need to be repeated for the other wingmen, and other items in the list of aliases shown in the editor. Refer to the VAICOM manual for instructions on how to do this.

## 2. VAICOM PRO VoiceAttack profile

The default VAICOM PRO profile that is imported into VoiceAttack requires modifications for running the `send_command.py` application with `start` or `stop` when TX buttons are pressed and released. There are also changes required to the import for the "When I say" keyword collections as wildcards (`*`) are not supported.

There are two options:
- The first is to import the "WhisperAttack for VAICOM PRO.vap" profile provided here that contains these changes. This is the recommended option as provides a good base and can be used as a reference when updating with your own keyword collections.
- The other is to duplicate and modify your existing profile. This means you can revert to the original profile if you break anything to start these steps again or compare differences.

**TODO:** Add instructions and information on what needs to be modified in the profile keyword collections and other extension packs.

### Disable speech recognition

You need to disable speech recognition in VoiceAttack so that only the Whisper transcribed commands are used. If you do not do so then you get duplicate commands issued, once for the normal Windows speech recognition engine, and then a second one from the Whisper transcribed text that is sent to VA. This requires a restart of VoiceAttack and you should now see the message stating voice recognition is disabled.

### Run command for each TX button

For each of the TX button press and release commands you need to add an associated `Run application` action for the WhisperAttack `send_command.py`.

For press buttons this needs a parameter of `start` and for release buttons this needs a parameter of `stop`

## 3. Start the Valhalla Whisper Server

VAICOM PRO requires that VoiceAttack be run as administrator, see the VAICOM docs (there is an option in VoiceAttack to enable this).

Running the `whisper_server.py` in the `WhisperAttack Valhalla` directory will execute VoiceAttack commands with administrator permissions. If you do not run the Valhalla version then you will get an error message in the console log output stating elevated permissions required when it attempts to send the transcribed text to VoiceAttack.

## 4. Start VAICOM PRO and DCS

Start VAICOM PRO, then start DCS and jump into an instant action mission for testing. Turn on your plane's battery and radio and then use the correct TX button for the relevant radio. For example, requesting startup from the ATC. You may need to issue one press/release with "ATC Select" to select the recipient, and then another press/release for "Request startup".

You should see the following occur:
1. The whisper server transcribe your spoken words to text and sends them to VoiceAttack
1. VoiceAttack locate the correct "When I say" command and send it to VAICOM
1. The associated radio command made in DCS