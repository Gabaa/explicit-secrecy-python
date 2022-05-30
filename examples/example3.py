import expsec

# Unsafe: h is leaked
h = 4
l = expsec.Public(6)
l = h
print(l)
