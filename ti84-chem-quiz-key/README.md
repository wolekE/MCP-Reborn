# CHEMKEY: Chemistry Practice Quiz answer key for the TI-84

A TI-BASIC program that stores all 30 answers and explanations from the
*Chemistry Practice Quiz: Answer Key*.

| File | Calculator |
|------|------------|
| `CHEMKEY-CE.8xp` | TI-84 Plus CE (also CE-T / CE Python), 26×10 screen |
| `CHEMKEY-84PLUS.8xp` | TI-84 Plus / TI-84 Plus Silver Edition, 16×8 screen |

Both install as `prgmCHEMKEY`. The two files hold the same content, laid out for each screen size.

## Put it on the calculator

1. Install **TI Connect CE** (free from education.ti.com). It works with both models.
2. Plug the calculator in over USB.
3. Drag the matching `.8xp` file onto the calculator in TI Connect CE and send it.
4. On the calculator press `prgm`, choose **CHEMKEY**, then press `enter` twice.

The text uses lowercase letters, `²` and `ᴇ`. The calculator can show these but you can't type
them on its keypad, so send the file from a computer instead of typing it in.

## Using it

The menu has these options:

- **GO TO QUESTION**: type a number from 1 to 30.
- **BROWSE ALL**: starts at question 1.
- **ANSWER LIST**: shows all 30 letters on one screen.
- **HELP**: shows the key guide.
- **QUIT**: exits.

On a question screen:

| Key | Action |
|-----|--------|
| ◄ / ► | previous / next question (wraps 30 → 1) |
| ▲ / ▼ | scroll a long explanation (`v1/2` in the footer means there is more) |
| `enter` | next page, or next question when on the last page |
| `clear` | back to the menu |

The program uses the variables `N`, `P`, `K`, `A`, `X` and `Str9`. `Str9` is deleted when you quit.

## Rebuilding

The answer text lives in `build_chemkey.py`. To change it, edit the file and rebuild:

```sh
pip install tivars
python3 build_chemkey.py   # writes the .8xp files and readable .txt listings
python3 test_chemkey.py    # runs both programs in a strict TI-BASIC simulator
```

`test_chemkey.py --show` prints every screen as the calculator would draw it.
