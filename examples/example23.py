"""
Safe

expsec_public: b1, b2, c1, c2
"""

a1 = [1, 2, 3]
b1 = [4, 5, 6]
if a1 == b1:
    c1 = a1
else:
    c1 = b1
print(c1)

a2 = [1, 2, 3]
b2 = [4, 5, 6]
if a2 != b2:
    c2 = b2
else:
    c2 = a2
print(c2)
