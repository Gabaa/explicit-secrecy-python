"""
Unsafe: This declassifies `b`, but not `a`

expsec_public:
"""

a = 10
b = a
expsec.declassify(b)
print(a)
