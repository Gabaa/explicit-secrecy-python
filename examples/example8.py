import expsec

# Safe
a = 10
b = expsec.Public(20)
if a < 0:
    expsec.declassify(a)
else:
    a = b
print(a)
