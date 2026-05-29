# 

Mostly vibecoded minimal bytebeat editors for terminal and browser.

## Guidelines:

- Minimalistic 
- Posfix/RPN
- Hex values
- Real Time eval

## Install

Clone this repo, then run this on the new directory:

```sh
python3 -m venv venv            ;
. /bin/activate                 ;
pip install -r requirements.txt
```

Once you set the proper enviroment like that, you should be able to run the program.

```sh
bash run
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
- `A` insert at the end
- `!` pause/resume eval
- `$` go to the end 
- `q` quit
- `0-f` replace with value
- `<(<<),>(>>),&,|,^,+,-,*,/,%` replace with operator

## Guide/Tutorial

See **minimal.md** for hints and tips.
