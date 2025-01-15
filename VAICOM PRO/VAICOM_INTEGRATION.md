# VAICOM PRO Integration

VAICOM PRO is a VoiceAttack plugin used to integrate with Digital Combat Simulator (DCS) for communicating with AI units without needing to use the F10 comms menus.

These instructions detail how to integrate Whisper server with VoiceAttack and VAICOM PRO.

**WARNING:** These instructions are a work in progress. WhisperAttack is in beta and things are subject to change.

The VAICOM PRO manual can be found on the VAICOM PRO Community Discord server.

An example VoiceAttack profile [WhisperAttack for VAICOM PRO.vap](WhisperAttack%20for%20VAICOM%20PRO.vap) is available here which is based on the default VAICOM PRO one, with updates made for Whisper support. This can be imported into VoiceAttack and used for your purposes.

## VAICOM PRO VSPX Speech Processing Mode

Within the VAICOM configuration the speech processing engine must be set to VSPX in the preferences. This is due to VoiceAttack not supporting
wildcard (`*`) characters when matching "When I say" commands when it is executed by the Whisper server. This lack of support means that there must
be an exact match on the text between wildcards. This breaks the VAICOM integration as it does not match on the full sentences that you speak.

The exported key words from the VAICOM database when run in this mode use official supported "When I say" VoiceAttack syntax that is required for Whisper.
This syntax allows for full sentences, with optional words and dynamic use of participant names etc.

**TODO:** document any updates required for the VSPX key words exported from VAICOM to handle existing `*` wild cards, and the correct order of key words
for dynamic participants in sentences.

## VAICOM PRO keywords database

The VAICOM PRO configuration contains an editor that can be used to add aliases for commands. WhisperAttack converts textual numbers to numerical values, e.g. "two" is 2. Because of this aliases will need to be added for keywords that contain textual numbers. For example, your wingman has the existing aliases of "two", "winger", and "bozo". You will need to add another alias for this with a value of `1`. This will need to be repeated for the other wingmen, and other items in the list of aliases shown in the editor. Refer to the VAICOM manual for instructions on how to do this.

![keywords database](./screenshots/VAICOM%20keywords%20database.png)

## VAICOM PRO VoiceAttack profile

The default VAICOM PRO profile that is imported into VoiceAttack requires modifications for running the `send_command.py` application with `start` or `stop` when TX buttons are pressed and released. There are also changes required to the import for the "When I say" keyword collections as wildcards (`*`) are not supported.

There are two options:
- The first is to import the "WhisperAttack for VAICOM PRO.vap" profile provided here that contains these changes. This is the recommended option as provides a good base and can be used as a reference when updating with your own keyword collections. The key words in this profile have been updated to remove other occurrances of
the `*` wildcard syntax and the correct ordering of participant and wingman callsigns in dynamic commands.
- The other is to duplicate and modify your existing profile. This means you can revert to the original profile if you break anything to start these steps again or compare differences. This will require you to update your VSPX exported keywords for the modifiying dynamic sentences containing participants and sentence structure.

**TODO:** Add instructions and information on what needs to be modified in the profile keyword collections and other extension packs.

### Disable speech recognition

You need to disable speech recognition in VoiceAttack so that only the Whisper transcribed commands are used. If you do not do so then you get duplicate commands issued, once for the normal Windows speech recognition engine, and then a second one from the Whisper transcribed text that is sent to VA. This requires a restart of VoiceAttack and you should now see the message stating voice recognition is disabled.

### Run command for each TX button

For each of the TX button press and release commands you need to add an associated `Run application` action for the WhisperAttack `send_command.py`.

- Open each Push-To-Talk button command
- Go to **Other > Windows > Run application** and enter the path and `send_command.py`
- The **With these parameters** for press buttons need a parameter of `start` and for release buttons this needs a parameter of `stop`
- Select the added action and click **Up** so that this occurs first in the sequence

![Add run application to push to talk](./screenshots/Add%20run%20application%20to%20push%20to%20talk.png)

This needs to be done for all TX buttons in use.

![Start and stop on all tx buttons](./screenshots/Start%20and%20stop%20on%20all%20tx%20buttons.png)


## Testing VAICOM integration

Start the WhisperAttack server, VAICOM PRO, then start DCS and jump into an instant action mission for testing. Turn on your plane's battery and radio and then use the correct TX button for the relevant radio. For example, requesting startup from the ATC. You may need to issue one press/release with "ATC Select" to select the recipient, and then another press/release for "Request startup".

As per the VAICOM documentation when participants are used in the voice command when using the VSPX mode then they should be said with no pauses. For example, "ATC request startup". When using WhisperAttack this would also be required as it says the full sentence in one go, with no pause between participant and command, hence does not wait for an acknoledgement of the participant prior to issuing the command.

You should see the following occur:
1. The whisper server transcribe your spoken words to text and sends them to VoiceAttack
1. VoiceAttack locate the correct "When I say" command and send it to VAICOM
1. The associated radio command made in DCS