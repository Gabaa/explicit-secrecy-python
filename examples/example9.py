import expsec

# Unsafe: This declassifies `b`, but not `a`
a = 10
b = expsec.Public(a)
print(a)
