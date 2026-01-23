# 

This is a small terminal bytebeat editor that I made with IA following my own preferences:

- Minimalistic UI
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

You can use the docker version but need to adjust the samplerate to default in line 79:

```python
    samplerate=44100,
```

...instead of 

```python
    samplerate=SAMPLE_RATE,
```

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

- `i` insert new term (default 0000)
- `x` delete term
- `u` undo
- `s` quick save expression
- `q` quit
- `up/down` increase/decrease digit
- `left/right` move cursor
- `0,1,2,3,4,5,6,7,8,9,a,b,c,d,e,f` value
- `<(<<),>(>>),&,|,^,+,-,*,/,%` operators
