import expsec

# Unsafe, l * h is leaked
l = expsec.Public(3)
h = 7
if l == 0:
    print(l * h)
else:
    pass
