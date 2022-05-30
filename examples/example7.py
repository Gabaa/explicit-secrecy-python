import expsec

# Unsafe
a = 10
if a < 0:
    expsec.declassify(a)
else:
    pass
print(a)
