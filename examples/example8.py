import expsec

# Safe: `a` is either declassified or assigned public value
a = 10
b = expsec.Public(20)
if a < 0:
    expsec.declassify(a)
else:
    a = b
print(a)
