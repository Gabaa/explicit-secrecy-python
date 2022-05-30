import expsec

# Safe: l overwrites h
h = 4
l = expsec.Public(6)
h = l
print(h)
