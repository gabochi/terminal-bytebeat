# Minimal bytebeats guidelines
This serves both as a guide to create very simple yet variant bytebeats and general steps for live improvisation.

## 1. Base waveform
Use OR to shape a base waveform.  Hint: nibbles work as high/low frequency component.

```
t 9c |
```

*OR will shape the wave but also pass big values of t, unlike AND that limits the output, you'll see why this is important:*

## 2. Sequence
Truncate in any point to generate a sequence (jumps will produce percussive accents):

```
t 9C | B3 %
```

Biger operands will produce longer/lower sequences:

```
t 39C | B3 %
```

```
t 8C | 3B3 %
```

---

## 3. Envelopes
Now there are many options for re-shaping the result that work as somekind of envelope:


## 4. OR all the way
Use OR to re-shape the result.

```
t 8C | 3B3 % 50 |
```

## 5. ADD or SUBSTRACT
Adding or substracting a constant value will change accents and distortion.

```
t 8C | 3B3 % 50 | 10 +
```

## 6. Use t instead of fixed values
You can always replace a fixed value for a t.

```
t 8C | 3B3 % t |
```

Add or substract again for accents/distortion.

```
t 8C | 3B3 % t | 22 +
```


## 7. Slower envelopes
Right shift second t for slower envelopes.

```
t 8C | 3B3 % t 2 >> |
```

```
t 8C | 3B3 % t 2 >> | 60 -
```

## 8. Add or substract t
Forget about OR, directly add or substract a slower t

```
t 8C | 3B3 % t 2 >> +
```

```
t BC | 3B3 % t 3 >> +
```
## 9. Staccato envelopes
Indeed, forget about adding and substracting too.  Shifting left or right with the precise speed will produce a nice staccatto:

```
t BC | 3B3 % t 5 >> <<
```

```
t BC | 3B3 % t 5 >> >>
```

Use shifts and multiplication to shape the amplitude and change the beat

```
t BC | 3B3 % t 5 >> >> 6 <<
```

```
t BC | 3B3 % t 5 >> >> A *
```

---

# A. Save, analyze
Save your experiments so you can later reproduce and analyze them.  **Keep your beats simple** so you can exploit the real potential and also smaller expressions are easier to understand.  Happy bytebeats, see you around!
