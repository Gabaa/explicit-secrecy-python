"""
Unsafe: `a` may be secret

expsec_public: 
"""

a = 10
if a < 0:
    expsec.declassify(a)
else:
    pass
print(a)
