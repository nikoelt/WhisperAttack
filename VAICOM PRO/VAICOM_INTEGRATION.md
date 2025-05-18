# Vaicom Integration

Vaicom is a VoiceAttack plugin used to integrate with Digital Combat Simulator (DCS) for communicating with AI units without needing to use the F10 comms menus.

These instructions detail how to integrate Whisper server with VoiceAttack and Vaicom.

The Vaicom manual can be found on the Vaicom Community Discord server.

## Vaicom VSPX Speech Processing Mode

Within the Vaicom configuration the speech processing engine must be set to VSPX in the preferences. This is due to VoiceAttack not supporting
wildcard (`*`) characters when matching "When I say" commands when it is executed by the Whisper server. This lack of support means that there must
be an exact match on the text between wildcards. This breaks the Vaicom integration as it does not match on the full sentences that you speak.

The exported key words from the Vaicom database when run in this mode use official supported "When I say" VoiceAttack syntax that is required for Whisper.
This syntax allows for full sentences, with optional words and dynamic use of participant names etc.

## Vaicom keywords database

The Vaicom configuration contains an editor that can be used to add aliases for commands. WhisperAttack converts textual numbers to numerical values, e.g. "two" is 2. Because of this aliases will need to be added for keywords that contain textual numbers. For example, your wingman has the existing aliases of "two", "winger", and "bozo". You will need to add another alias for this with a value of `2`. This will need to be repeated for the other wingmen, and other items in the list of aliases shown in the editor. Refer to the Vaicom manual for instructions on how to do this.

![keywords database](./screenshots/Vaicom%20keywords%20database.png)

**NOTE:** As of Vaicom 3.0.0 support has been added so that wingmen, and other items, are already present with numerical values so do not need to be updated. Numerical values would still need to be applied to other items if ncessary, e.g. the JTAC command "Ten seconds" would need an alias of "10 Seconds".

## Vaicom VoiceAttack profile

The default Vaicom profile that is imported into VoiceAttack requires modifications for executing the `WASC` (WhisperAttackSendCommand) plugin with the `Start Whisper Recording` or `Stop Whisper Recording` Plugin Context value when TX buttons are pressed and released.

### Disable speech recognition

You need to disable speech recognition in VoiceAttack so that only the Whisper transcribed commands are used. If you do not do so then you get duplicate commands issued, once for the normal Windows speech recognition engine, and then a second one from the Whisper transcribed text that is sent to VA. This requires a restart of VoiceAttack and you should now see the message stating voice recognition is disabled.

### Run command for each TX button

For each of the TX button press and release commands you need to add an associated `Execute external plugin` action for the WhisperAttack `WASC` plugin. See the README for instructions on installing this plugin into VoiceAttack.

- Open each Push-To-Talk button command
- Go to **Other > Advanced > Execute and External Plugin Function** and select the `WASC` plugin from the Plugin dropdown
- The **Plugin Context** for press buttons need a value of `Start Whisper Recording` and for release buttons this needs a value of `Stop Whisper Recording`
- Select the added action and click **Up** so that this occurs first in the sequence

![Add run application to push to talk](./screenshots/Add%20execute%20plugin%20to%20push%20to%20talk.png)

This needs to be done for all TX buttons in use.

![Start and stop on all tx buttons](./screenshots/Start%20and%20stop%20on%20all%20tx%20buttons.png)


## Testing Vaicom integration

Start the WhisperAttack server, Vaicom, then start DCS and jump into an instant action mission for testing. Turn on your plane's battery and radio and then use the correct TX button for the relevant radio. For example, requesting startup from the ATC. You may need to issue one press/release with "ATC Select" to select the recipient, and then another press/release for "Request startup".

As per the Vaicom documentation when participants are used in the voice command when using the VSPX mode then they should be said with no pauses. For example, "ATC request startup". When using WhisperAttack this would also be required as it says the full sentence in one go, with no pause between participant and command, hence does not wait for an acknoledgement of the participant prior to issuing the command.

You should see the following occur:
1. The whisper server transcribe your spoken words to text and sends them to VoiceAttack
1. VoiceAttack locate the correct "When I say" command and send it to Vaicom
1. The associated radio command made in DCS

![WhisperAttack UI and VoiceAttack](./screenshots/WhisperAttack%20UI%20and%20VoiceAttack.png)
