// CicloAuto: micro:bit on the rear of the bike. Its LED matrix is the turn signal and brake light.
// The phone (CicloAuto app) decides everything and talks to it over Bluetooth. Messages (one per line):
//   "SR" or "R" = right signal   "SL" or "L" = left signal   "S0" or "0" = signals off
//   "B1" = brake on (full square)   "B0" = brake off
//   "H1" = hazard on (whole matrix flashing, used after a crash / SOS)   "H0" = hazard off
// The MakeCode simulator has no Bluetooth: use A (left), B (right) and A+B (off) to test the signals there.
// Mount the micro:bit upright with the screen facing backwards: riders behind you see ">" on the correct side.

let signal = 0         // 0 = off, 1 = right, -1 = left
let brake = 0          // 1 = the phone detected braking
let hazard = 0         // 1 = crash / SOS: flash to get attention
let frame = 0          // step of the signal animation
let connected = 0
let command = ""

bluetooth.startUartService()
led.setBrightness(255)

bluetooth.onBluetoothConnected(function () {
    connected = 1
    basic.showIcon(IconNames.Yes)
    basic.pause(500)
    basic.clearScreen()
})

bluetooth.onBluetoothDisconnected(function () {
    connected = 0
    signal = 0
    brake = 0
    hazard = 0
    basic.showIcon(IconNames.No)
    basic.pause(500)
    basic.clearScreen()
})

// Read each message ONCE and keep it in a variable
bluetooth.onUartDataReceived(serial.delimiters(Delimiters.NewLine), function () {
    command = bluetooth.uartReadUntil(serial.delimiters(Delimiters.NewLine))
    if (command == "R" || command == "SR") {
        signal = 1
        frame = 0
    } else if (command == "L" || command == "SL") {
        signal = -1
        frame = 0
    } else if (command == "0" || command == "S0") {
        signal = 0
    } else if (command == "B1") {
        brake = 1
    } else if (command == "B0") {
        brake = 0
    } else if (command == "H1") {
        hazard = 1
        frame = 0
    } else if (command == "H0") {
        hazard = 0
    }
})

// Buttons: only for testing in the MakeCode simulator (not used on the bike)
input.onButtonPressed(Button.A, function () {
    if (signal == -1) {
        signal = 0
    } else {
        signal = -1
    }
    frame = 0
    notifyPhone()
})
input.onButtonPressed(Button.B, function () {
    if (signal == 1) {
        signal = 0
    } else {
        signal = 1
    }
    frame = 0
    notifyPhone()
})
input.onButtonPressed(Button.AB, function () {
    signal = 0
    notifyPhone()
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

// The only loop that draws on the screen. Priority: hazard, then brake, then signal.
basic.forever(function () {
    if (hazard == 1) {
        if (frame % 2 == 0) {
            basic.showLeds(`
                # # # # #
                # # # # #
                # # # # #
                # # # # #
                # # # # #
                `, 0)
        } else {
            basic.clearScreen()
        }
        frame = (frame + 1) % 4
    } else if (brake == 1) {
        basic.showLeds(`
            # # # # #
            # # # # #
            # # # # #
            # # # # #
            # # # # #
            `, 0)
    } else if (signal == 1) {
        showRight(frame)
        frame = (frame + 1) % 4
    } else if (signal == -1) {
        showLeft(frame)
        frame = (frame + 1) % 4
    } else {
        basic.clearScreen()
    }
    basic.pause(130)
})

// ">" running to the right (the 4th frame is blank = blinking effect)
function showRight (q: number) {
    if (q == 0) {
        basic.showLeds(`
            # . . . .
            . # . . .
            . . # . .
            . # . . .
            # . . . .
            `, 0)
    } else if (q == 1) {
        basic.showLeds(`
            . # . . .
            . . # . .
            . . . # .
            . . # . .
            . # . . .
            `, 0)
    } else if (q == 2) {
        basic.showLeds(`
            . . # . .
            . . . # .
            . . . . #
            . . . # .
            . . # . .
            `, 0)
    } else {
        basic.clearScreen()
    }
}

// "<" running to the left
function showLeft (q: number) {
    if (q == 0) {
        basic.showLeds(`
            . . . . #
            . . . # .
            . . # . .
            . . . # .
            . . . . #
            `, 0)
    } else if (q == 1) {
        basic.showLeds(`
            . . . # .
            . . # . .
            . # . . .
            . . # . .
            . . . # .
            `, 0)
    } else if (q == 2) {
        basic.showLeds(`
            . . # . .
            . # . . .
            # . . . .
            . # . . .
            . . # . .
            `, 0)
    } else {
        basic.clearScreen()
    }
}
