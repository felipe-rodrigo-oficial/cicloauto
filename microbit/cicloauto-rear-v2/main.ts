// CicloAuto rear light, micro:bit V2
// The micro:bit sits on the back of the bike (screen facing backwards). The phone (CicloAuto app) decides everything
// and sends one message per line over Bluetooth UART:
//   SR / SL / S0  right signal / left signal / signals off      (R, L, 0 also accepted)
//   B1 / B0       brake light on / off
//   H1 / H0       hazard on / off (after a crash / SOS: whole matrix flashing + siren on the V2 speaker)
// micro:bit -> phone: SR / SL / S0 when buttons A / B are used (for testing).
//
// V2 extras
//   speaker: soft "tick" while a turn signal is on, siren while the hazard is on
//   touch the gold logo: sound on / off (a note confirms)
// Screen
//   waiting for the phone: one dim dot blinking in the center
//   brake + signal together: the arrow stays bright over a dimmed full square, so both are readable
//
// MakeCode project settings: extension "bluetooth", and "No Pairing Required" (already set in pxt.json, see microbit/README.md).

const BRIGHT = 255     // arrow / brake
const DIM = 40         // background behind the arrow while braking
const STEP_MS = 130    // animation step (same pace as the app's virtual micro:bit)

let signal = 0         // 0 = off, 1 = right, -1 = left
let brake = 0
let hazard = 0
let frame = 0
let connected = 0
let sound = 1
let command = ""

bluetooth.startUartService()
led.setBrightness(255)
music.setVolume(160)

bluetooth.onBluetoothConnected(function () {
    connected = 1
    basic.showIcon(IconNames.Yes, 0)
    if (sound == 1) music.play(music.tonePlayable(Note.C5, music.beat(BeatFraction.Eighth)), music.PlaybackMode.InBackground)
    basic.pause(500)
    basic.clearScreen()
})

bluetooth.onBluetoothDisconnected(function () {
    connected = 0
    signal = 0
    brake = 0
    hazard = 0
    basic.showIcon(IconNames.No, 0)
    basic.pause(500)
    basic.clearScreen()
})

// Read each message once and keep it in a variable
bluetooth.onUartDataReceived(serial.delimiters(Delimiters.NewLine), function () {
    command = bluetooth.uartReadUntil(serial.delimiters(Delimiters.NewLine)).trim()
    if (command == "R" || command == "SR") {
        if (signal != 1) frame = 0
        signal = 1
    } else if (command == "L" || command == "SL") {
        if (signal != -1) frame = 0
        signal = -1
    } else if (command == "0" || command == "S0") {
        signal = 0
    } else if (command == "B1") {
        brake = 1
    } else if (command == "B0") {
        brake = 0
    } else if (command == "H1") {
        if (hazard != 1) frame = 0
        hazard = 1
    } else if (command == "H0") {
        hazard = 0
    }
})

// Buttons: for testing (MakeCode simulator, or on the bench). They also tell the phone.
input.onButtonPressed(Button.A, function () {
    signal = signal == -1 ? 0 : -1
    frame = 0
    notifyPhone()
})
input.onButtonPressed(Button.B, function () {
    signal = signal == 1 ? 0 : 1
    frame = 0
    notifyPhone()
})
input.onButtonPressed(Button.AB, function () {
    signal = 0
    notifyPhone()
})

// V2: touch the logo to turn the sound on / off
input.onLogoEvent(TouchButtonEvent.Pressed, function () {
    sound = 1 - sound
    if (sound == 1) {
        music.play(music.tonePlayable(Note.G5, music.beat(BeatFraction.Eighth)), music.PlaybackMode.InBackground)
    } else {
        music.stopAllSounds()
    }
})

function notifyPhone () {
    if (connected == 1) {
        if (signal == 1) {
            bluetooth.uartWriteLine("SR")
        } else if (signal == -1) {
            bluetooth.uartWriteLine("SL")
        } else {
            bluetooth.uartWriteLine("S0")
        }
    }
}

function fill (b: number) {
    for (let x = 0; x < 5; x++) {
        for (let y = 0; y < 5; y++) {
            led.plotBrightness(x, y, b)
        }
    }
}

// chevron ">" (dir 1) or "<" (dir -1) moving one column per step; step 3 is blank = blink
function arrow (dir: number, q: number) {
    if (q > 2) return
    const rows = [0, 1, 2, 1, 0]
    for (let y = 0; y < 5; y++) {
        let x = q + rows[y]
        if (dir < 0) x = 4 - x
        led.plotBrightness(x, y, BRIGHT)
    }
}

// The only loop that draws (and makes sound). Priority: hazard, then brake / signal.
basic.forever(function () {
    if (hazard == 1) {
        fill(frame % 2 == 0 ? BRIGHT : 0)
        if (sound == 1 && frame % 2 == 0) {
            music.play(music.tonePlayable(frame % 4 == 0 ? 1400 : 1000, STEP_MS), music.PlaybackMode.InBackground)
        }
    } else if (signal != 0) {
        fill(brake == 1 ? DIM : 0)
        arrow(signal, frame % 4)
        if (sound == 1 && frame % 4 == 0) {
            music.play(music.tonePlayable(2200, 12), music.PlaybackMode.InBackground)   // "tick", like a car
        }
    } else if (brake == 1) {
        fill(BRIGHT)
    } else if (connected == 0) {
        basic.clearScreen()
        if (frame % 16 == 0) led.plotBrightness(2, 2, 30)   // waiting for the phone
    } else {
        basic.clearScreen()
    }
    frame = (frame + 1) % 16
    basic.pause(STEP_MS)
})
