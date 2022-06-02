"""
Safe: `a` is either declassified or assigned public value

expsec_public: b
"""

a = 10
b = 20
if a < 0:
    expsec.declassify(a)
else:
    a = b
print(a)
