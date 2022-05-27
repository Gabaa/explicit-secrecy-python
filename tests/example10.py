import expsec

# Unsafe
a = 10
b = a
expsec.declassify(b)
print(a)
