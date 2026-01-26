# 

This is a small terminal bytebeat editor that I made with IA following my own preferences:

- Terminal based
- Minimalistic 
- Posfix/RPN
- Hex values
- Limited set of operators
- Real Time eval
- Increase/Decrease digits
- Rotate operators
- Quick shortcuts

## Install

```sh
python3 -m venv venv            ;
. /bin/activate                 ;
pip install -r requirements.txt
```

Once you set the proper enviroment like that, you should be able to run the program.

```sh
python3 main.py
```

## Dockerfile

You can use the docker version but surely you'll need to change the samplerate in the code, check the commented block.

Then build the image.

```sh
docker build -t bytebeat-app .
```

And run (good luck):

```sh
docker run -it --rm \
    --device /dev/snd \
    -e TERM=$TERM \
    bytebeat-app
```

*Mount a volume (-v) if you want to keep bytebeat_saves.txt*

## Controls

- `hjkl` move cursor, increase/decrease digit
- `i` insert new term to the right
- `x` delete term
- `u` undo
- `w` quick save expression
- `W` next start of term
- `B` previous start of term
- `E` next end of term
- `!` pause/resume eval
- `$` end of expression
- `q` quit
- `0-f` replace with value
- `<(<<),>(>>),&,|,^,+,-,*,/,%` replace with operator

## Guide/Tutorial

See **minimal.md** for hints and tips.
