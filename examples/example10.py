import expsec

# Unsafe: This declassifies `b`, but not `a`
a = 10
b = a
expsec.declassify(b)
print(a)
