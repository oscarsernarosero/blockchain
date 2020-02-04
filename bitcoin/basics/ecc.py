from io import BytesIO
from random import randint
from unittest import TestCase

import struct
import logging

import hashlib
import hmac

from helper import encode_base58_checksum, hash160

logger = logging.getLogger(__name__)


class FieldElement:

    def __init__(self, num, prime):
        if num >= prime or num < 0:
            error = 'Num {} not in field range 0 to {}'.format(
                num, prime - 1)
            raise ValueError(error)
        self.num = num
        self.prime = prime

    def __repr__(self):
        return 'FieldElement_{}({})'.format(self.prime, self.num)

    def __eq__(self, other):
        if other is None:
            return False
        return self.num == other.num and self.prime == other.prime

    def __ne__(self, other):
        # this should be the inverse of the == operator
        return not (self == other)

    def __add__(self, other):
        if self.prime != other.prime:
            raise TypeError('Cannot add two numbers in different Fields')
        # self.num and other.num are the actual values
        # self.prime is what we need to mod against
        num = (self.num + other.num) % self.prime
        # We return an element of the same class
        return self.__class__(num, self.prime)

    def __sub__(self, other):
        if self.prime != other.prime:
            raise TypeError('Cannot subtract two numbers in different Fields')
        # self.num and other.num are the actual values
        # self.prime is what we need to mod against
        num = (self.num - other.num) % self.prime
        # We return an element of the same class
        return self.__class__(num, self.prime)

    def __mul__(self, other):
        if self.prime != other.prime:
            raise TypeError('Cannot multiply two numbers in different Fields')
        # self.num and other.num are the actual values
        # self.prime is what we need to mod against
        num = (self.num * other.num) % self.prime
        # We return an element of the same class
        return self.__class__(num, self.prime)

    def __pow__(self, exponent):
        n = exponent % (self.prime - 1)
        num = pow(self.num, n, self.prime)
        return self.__class__(num, self.prime)

    def __truediv__(self, other):
        if self.prime != other.prime:
            raise TypeError('Cannot divide two numbers in different Fields')
        # self.num and other.num are the actual values
        # self.prime is what we need to mod against
        # use fermat's little theorem:
        # self.num**(p-1) % p == 1
        # this means:
        # 1/n == pow(n, p-2, p)
        num = (self.num * pow(other.num, self.prime - 2, self.prime)) % self.prime
        # We return an element of the same class
        return self.__class__(num, self.prime)

    def __rmul__(self, coefficient):
        num = (self.num * coefficient) % self.prime
        return self.__class__(num=num, prime=self.prime)


class FieldElementTest(TestCase):

    def test_ne(self):
        a = FieldElement(2, 31)
        b = FieldElement(2, 31)
        c = FieldElement(15, 31)
        self.assertEqual(a, b)
        self.assertTrue(a != c)
        self.assertFalse(a != b)

    def test_add(self):
        a = FieldElement(2, 31)
        b = FieldElement(15, 31)
        self.assertEqual(a + b, FieldElement(17, 31))
        a = FieldElement(17, 31)
        b = FieldElement(21, 31)
        self.assertEqual(a + b, FieldElement(7, 31))

    def test_sub(self):
        a = FieldElement(29, 31)
        b = FieldElement(4, 31)
        self.assertEqual(a - b, FieldElement(25, 31))
        a = FieldElement(15, 31)
        b = FieldElement(30, 31)
        self.assertEqual(a - b, FieldElement(16, 31))

    def test_mul(self):
        a = FieldElement(24, 31)
        b = FieldElement(19, 31)
        self.assertEqual(a * b, FieldElement(22, 31))

    def test_rmul(self):
        a = FieldElement(24, 31)
        b = 2
        self.assertEqual(b * a, a + a)

    def test_pow(self):
        a = FieldElement(17, 31)
        self.assertEqual(a**3, FieldElement(15, 31))
        a = FieldElement(5, 31)
        b = FieldElement(18, 31)
        self.assertEqual(a**5 * b, FieldElement(16, 31))

    def test_div(self):
        a = FieldElement(3, 31)
        b = FieldElement(24, 31)
        self.assertEqual(a / b, FieldElement(4, 31))
        a = FieldElement(17, 31)
        self.assertEqual(a**-3, FieldElement(29, 31))
        a = FieldElement(4, 31)
        b = FieldElement(11, 31)
        self.assertEqual(a**-4 * b, FieldElement(13, 31))


class Point:

    def __init__(self, x, y, a, b):
        self.a = a
        self.b = b
        self.x = x
        self.y = y
        # x being None and y being None represents the point at infinity
        # Check for that here since the equation below won't make sense
        # with None values for both.
        if self.x is None and self.y is None:
            return
        # make sure that the elliptic curve equation is satisfied
        # y**2 == x**3 + a*x + b
        if self.y**2 != self.x**3 + a * x + b:
            # if not, throw a ValueError
            raise ValueError('({}, {}) is not on the curve'.format(x, y))

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y \
            and self.a == other.a and self.b == other.b

    def __ne__(self, other):
        # this should be the inverse of the == operator
        return not (self == other)

    def __repr__(self):
        if self.x is None:
            return 'Point(infinity)'
        elif isinstance(self.x, FieldElement):
            return 'Point({},{})_{}_{} FieldElement({})'.format(
                self.x.num, self.y.num, self.a.num, self.b.num, self.x.prime)
        else:
            return 'Point({},{})_{}_{}'.format(self.x, self.y, self.a, self.b)

    def __add__(self, other):
        if self.a != other.a or self.b != other.b:
            raise TypeError('Points {}, {} are not on the same curve'.format(self, other))
        # Case 0.0: self is the point at infinity, return other
        if self.x is None:
            return other
        # Case 0.1: other is the point at infinity, return self
        if other.x is None:
            return self

        # Case 1: self.x == other.x, self.y != other.y
        # Result is point at infinity
        if self.x == other.x and self.y != other.y:
            return self.__class__(None, None, self.a, self.b)

        # Case 2: self.x ≠ other.x
        # Formula (x3,y3)==(x1,y1)+(x2,y2)
        # s=(y2-y1)/(x2-x1)
        # x3=s**2-x1-x2
        # y3=s*(x1-x3)-y1
        if self.x != other.x:
            s = (other.y - self.y) / (other.x - self.x)
            x = s**2 - self.x - other.x
            y = s * (self.x - x) - self.y
            return self.__class__(x, y, self.a, self.b)

        # Case 4: if we are tangent to the vertical line,
        # we return the point at infinity
        # note instead of figuring out what 0 is for each type
        # we just use 0 * self.x
        if self == other and self.y == 0 * self.x:
            return self.__class__(None, None, self.a, self.b)

        # Case 3: self == other
        # Formula (x3,y3)=(x1,y1)+(x1,y1)
        # s=(3*x1**2+a)/(2*y1)
        # x3=s**2-2*x1
        # y3=s*(x1-x3)-y1
        if self == other:
            s = (3 * self.x**2 + self.a) / (2 * self.y)
            x = s**2 - 2 * self.x
            y = s * (self.x - x) - self.y
            return self.__class__(x, y, self.a, self.b)

    def __rmul__(self, coefficient):
        coef = coefficient
        current = self
        result = self.__class__(None, None, self.a, self.b)
        while coef:
            if coef & 1:
                result += current
            current += current
            coef >>= 1
        return result


class PointTest(TestCase):

    def test_ne(self):
        a = Point(x=3, y=-7, a=5, b=7)
        b = Point(x=18, y=77, a=5, b=7)
        self.assertTrue(a != b)
        self.assertFalse(a != a)

    def test_on_curve(self):
        with self.assertRaises(ValueError):
            Point(x=-2, y=4, a=5, b=7)
        # these should not raise an error
        Point(x=3, y=-7, a=5, b=7)
        Point(x=18, y=77, a=5, b=7)

    def test_add0(self):
        a = Point(x=None, y=None, a=5, b=7)
        b = Point(x=2, y=5, a=5, b=7)
        c = Point(x=2, y=-5, a=5, b=7)
        self.assertEqual(a + b, b)
        self.assertEqual(b + a, b)
        self.assertEqual(b + c, a)

    def test_add1(self):
        a = Point(x=3, y=7, a=5, b=7)
        b = Point(x=-1, y=-1, a=5, b=7)
        self.assertEqual(a + b, Point(x=2, y=-5, a=5, b=7))

    def test_add2(self):
        a = Point(x=-1, y=1, a=5, b=7)
        self.assertEqual(a + a, Point(x=18, y=-77, a=5, b=7))


class ECCTest(TestCase):

    def test_on_curve(self):
        # tests the following points whether they are on the curve or not
        # on curve y^2=x^3-7 over F_223:
        # (192,105) (17,56) (200,119) (1,193) (42,99)
        # the ones that aren't should raise a ValueError
        prime = 223
        a = FieldElement(0, prime)
        b = FieldElement(7, prime)

        valid_points = ((192, 105), (17, 56), (1, 193))
        invalid_points = ((200, 119), (42, 99))

        # iterate over valid points
        for x_raw, y_raw in valid_points:
            x = FieldElement(x_raw, prime)
            y = FieldElement(y_raw, prime)
            # Creating the point should not result in an error
            Point(x, y, a, b)

        # iterate over invalid points
        for x_raw, y_raw in invalid_points:
            x = FieldElement(x_raw, prime)
            y = FieldElement(y_raw, prime)
            with self.assertRaises(ValueError):
                Point(x, y, a, b)

    def test_add(self):
        # tests the following additions on curve y^2=x^3-7 over F_223:
        # (192,105) + (17,56)
        # (47,71) + (117,141)
        # (143,98) + (76,66)
        prime = 223
        a = FieldElement(0, prime)
        b = FieldElement(7, prime)

        additions = (
            # (x1, y1, x2, y2, x3, y3)
            (192, 105, 17, 56, 170, 142),
            (47, 71, 117, 141, 60, 139),
            (143, 98, 76, 66, 47, 71),
        )
        # iterate over the additions
        for x1_raw, y1_raw, x2_raw, y2_raw, x3_raw, y3_raw in additions:
            x1 = FieldElement(x1_raw, prime)
            y1 = FieldElement(y1_raw, prime)
            p1 = Point(x1, y1, a, b)
            x2 = FieldElement(x2_raw, prime)
            y2 = FieldElement(y2_raw, prime)
            p2 = Point(x2, y2, a, b)
            x3 = FieldElement(x3_raw, prime)
            y3 = FieldElement(y3_raw, prime)
            p3 = Point(x3, y3, a, b)
            # check that p1 + p2 == p3
            self.assertEqual(p1 + p2, p3)

    def test_rmul(self):
        # tests the following scalar multiplications
        # 2*(192,105)
        # 2*(143,98)
        # 2*(47,71)
        # 4*(47,71)
        # 8*(47,71)
        # 21*(47,71)
        prime = 223
        a = FieldElement(0, prime)
        b = FieldElement(7, prime)

        multiplications = (
            # (coefficient, x1, y1, x2, y2)
            (2, 192, 105, 49, 71),
            (2, 143, 98, 64, 168),
            (2, 47, 71, 36, 111),
            (4, 47, 71, 194, 51),
            (8, 47, 71, 116, 55),
            (21, 47, 71, None, None),
        )

        # iterate over the multiplications
        for s, x1_raw, y1_raw, x2_raw, y2_raw in multiplications:
            x1 = FieldElement(x1_raw, prime)
            y1 = FieldElement(y1_raw, prime)
            p1 = Point(x1, y1, a, b)
            # initialize the second point based on whether it's the point at infinity
            if x2_raw is None:
                p2 = Point(None, None, a, b)
            else:
                x2 = FieldElement(x2_raw, prime)
                y2 = FieldElement(y2_raw, prime)
                p2 = Point(x2, y2, a, b)

            # check that the product is equal to the expected point
            self.assertEqual(s * p1, p2)


A = 0
B = 7
P = 2**256 - 2**32 - 977
N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141


class S256Field(FieldElement):

    def __init__(self, num, prime=None):
        super().__init__(num=num, prime=P)

    def __repr__(self):
        return '{:x}'.format(self.num).zfill(64)

    # tag::source2[]
    def sqrt(self):
        return self**((P + 1) // 4)
    # end::source2[]


class S256Point(Point):

    def __init__(self, x, y, a=None, b=None):
        a, b = S256Field(A), S256Field(B)
        if type(x) == int:
            super().__init__(x=S256Field(x), y=S256Field(y), a=a, b=b)
        else:
            super().__init__(x=x, y=y, a=a, b=b)

    def __repr__(self):
        if self.x is None:
            return 'S256Point(infinity)'
        else:
            return 'S256Point({}, {})'.format(self.x, self.y)

    def __rmul__(self, coefficient):
        coef = coefficient % N
        return super().__rmul__(coef)

    def verify(self, z, sig):
        # By Fermat's Little Theorem, 1/s = pow(s, N-2, N)
        s_inv = pow(sig.s, N - 2, N)
        # u = z / s
        u = z * s_inv % N
        # v = r / s
        v = sig.r * s_inv % N
        # u*G + v*P should have as the x coordinate, r
        total = u * G + v * self
        return total.x.num == sig.r

    # tag::source1[]
    def sec(self, compressed=True):
        '''returns the binary version of the SEC format'''
        if compressed:
            if self.y.num % 2 == 0:
                return b'\x02' + self.x.num.to_bytes(32, 'big')
            else:
                return b'\x03' + self.x.num.to_bytes(32, 'big')
        else:
            return b'\x04' + self.x.num.to_bytes(32, 'big') + \
                self.y.num.to_bytes(32, 'big')
    # end::source1[]

    # tag::source5[]
    def hash160(self, compressed=True):
        return hash160(self.sec(compressed))

    def address(self, compressed=True, testnet=False):
        '''Returns the address string'''
        h160 = self.hash160(compressed)
        if testnet:
            prefix = b'\x6f'
        else:
            prefix = b'\x00'
        return encode_base58_checksum(prefix + h160)
    # end::source5[]

    # tag::source3[]
    @classmethod
    def parse(self, sec_bin):
        '''returns a Point object from a SEC binary (not hex)'''
        if sec_bin[0] == 4:  # <1>
            x = int.from_bytes(sec_bin[1:33], 'big')
            y = int.from_bytes(sec_bin[33:65], 'big')
            return S256Point(x=x, y=y)
        is_even = sec_bin[0] == 2  # <2>
        x = S256Field(int.from_bytes(sec_bin[1:], 'big'))
        # right side of the equation y^2 = x^3 + 7
        alpha = x**3 + S256Field(B)
        # solve for left side
        beta = alpha.sqrt()  # <3>
        if beta.num % 2 == 0:  # <4>
            even_beta = beta
            odd_beta = S256Field(P - beta.num)
        else:
            even_beta = S256Field(P - beta.num)
            odd_beta = beta
        if is_even:
            return S256Point(x, even_beta)
        else:
            return S256Point(x, odd_beta)
    # end::source3[]
    


G = S256Point(
    0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
    0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)


class S256Test(TestCase):

    def test_order(self):
        point = N * G
        self.assertIsNone(point.x)

    def test_pubpoint(self):
        # write a test that tests the public point for the following
        points = (
            # secret, x, y
            (7, 0x5cbdf0646e5db4eaa398f365f2ea7a0e3d419b7e0330e39ce92bddedcac4f9bc, 0x6aebca40ba255960a3178d6d861a54dba813d0b813fde7b5a5082628087264da),
            (1485, 0xc982196a7466fbbbb0e27a940b6af926c1a74d5ad07128c82824a11b5398afda, 0x7a91f9eae64438afb9ce6448a1c133db2d8fb9254e4546b6f001637d50901f55),
            (2**128, 0x8f68b9d2f63b5f339239c1ad981f162ee88c5678723ea3351b7b444c9ec4c0da, 0x662a9f2dba063986de1d90c2b6be215dbbea2cfe95510bfdf23cbf79501fff82),
            (2**240 + 2**31, 0x9577ff57c8234558f293df502ca4f09cbc65a6572c842b39b366f21717945116, 0x10b49c67fa9365ad7b90dab070be339a1daf9052373ec30ffae4f72d5e66d053),
        )

        # iterate over points
        for secret, x, y in points:
            # initialize the secp256k1 point (S256Point)
            point = S256Point(x, y)
            # check that the secret*G is the same as the point
            self.assertEqual(secret * G, point)

    def test_verify(self):
        point = S256Point(
            0x887387e452b8eacc4acfde10d9aaf7f6d9a0f975aabb10d006e4da568744d06c,
            0x61de6d95231cd89026e286df3b6ae4a894a3378e393e93a0f45b666329a0ae34)
        z = 0xec208baa0fc1c19f708a9ca96fdeff3ac3f230bb4a7ba4aede4942ad003c0f60
        r = 0xac8d1c87e51d0d441be8b3dd5b05c8795b48875dffe00b7ffcfac23010d3a395
        s = 0x68342ceff8935ededd102dd876ffd6ba72d6a427a3edb13d26eb0781cb423c4
        self.assertTrue(point.verify(z, Signature(r, s)))
        z = 0x7c076ff316692a3d7eb3c3bb0f8b1488cf72e1afcd929e29307032997a838a3d
        r = 0xeff69ef2b1bd93a66ed5219add4fb51e11a840f404876325a1e8ffe0529a2c
        s = 0xc7207fee197d27c618aea621406f6bf5ef6fca38681d82b2f06fddbdce6feab6
        self.assertTrue(point.verify(z, Signature(r, s)))

    def test_sec(self):
        coefficient = 999**3
        uncompressed = '049d5ca49670cbe4c3bfa84c96a8c87df086c6ea6a24ba6b809c9de234496808d56fa15cc7f3d38cda98dee2419f415b7513dde1301f8643cd9245aea7f3f911f9'
        compressed = '039d5ca49670cbe4c3bfa84c96a8c87df086c6ea6a24ba6b809c9de234496808d5'
        point = coefficient * G
        self.assertEqual(point.sec(compressed=False), bytes.fromhex(uncompressed))
        self.assertEqual(point.sec(compressed=True), bytes.fromhex(compressed))
        coefficient = 123
        uncompressed = '04a598a8030da6d86c6bc7f2f5144ea549d28211ea58faa70ebf4c1e665c1fe9b5204b5d6f84822c307e4b4a7140737aec23fc63b65b35f86a10026dbd2d864e6b'
        compressed = '03a598a8030da6d86c6bc7f2f5144ea549d28211ea58faa70ebf4c1e665c1fe9b5'
        point = coefficient * G
        self.assertEqual(point.sec(compressed=False), bytes.fromhex(uncompressed))
        self.assertEqual(point.sec(compressed=True), bytes.fromhex(compressed))
        coefficient = 42424242
        uncompressed = '04aee2e7d843f7430097859e2bc603abcc3274ff8169c1a469fee0f20614066f8e21ec53f40efac47ac1c5211b2123527e0e9b57ede790c4da1e72c91fb7da54a3'
        compressed = '03aee2e7d843f7430097859e2bc603abcc3274ff8169c1a469fee0f20614066f8e'
        point = coefficient * G
        self.assertEqual(point.sec(compressed=False), bytes.fromhex(uncompressed))
        self.assertEqual(point.sec(compressed=True), bytes.fromhex(compressed))

    def test_address(self):
        secret = 888**3
        mainnet_address = '148dY81A9BmdpMhvYEVznrM45kWN32vSCN'
        testnet_address = 'mieaqB68xDCtbUBYFoUNcmZNwk74xcBfTP'
        point = secret * G
        self.assertEqual(
            point.address(compressed=True, testnet=False), mainnet_address)
        self.assertEqual(
            point.address(compressed=True, testnet=True), testnet_address)
        secret = 321
        mainnet_address = '1S6g2xBJSED7Qr9CYZib5f4PYVhHZiVfj'
        testnet_address = 'mfx3y63A7TfTtXKkv7Y6QzsPFY6QCBCXiP'
        point = secret * G
        self.assertEqual(
            point.address(compressed=False, testnet=False), mainnet_address)
        self.assertEqual(
            point.address(compressed=False, testnet=True), testnet_address)
        secret = 4242424242
        mainnet_address = '1226JSptcStqn4Yq9aAmNXdwdc2ixuH9nb'
        testnet_address = 'mgY3bVusRUL6ZB2Ss999CSrGVbdRwVpM8s'
        point = secret * G
        self.assertEqual(
            point.address(compressed=False, testnet=False), mainnet_address)
        self.assertEqual(
            point.address(compressed=False, testnet=True), testnet_address)


class Signature:

    def __init__(self, r, s):
        self.r = r
        self.s = s

    def __repr__(self):
        return 'Signature({:x},{:x})'.format(self.r, self.s)

    # tag::source4[]
    def der(self):
        rbin = self.r.to_bytes(32, byteorder='big')
        # remove all null bytes at the beginning
        rbin = rbin.lstrip(b'\x00')
        # if rbin has a high bit, add a \x00
        if rbin[0] & 0x80:
            rbin = b'\x00' + rbin
        result = bytes([2, len(rbin)]) + rbin  # <1>
        sbin = self.s.to_bytes(32, byteorder='big')
        # remove all null bytes at the beginning
        sbin = sbin.lstrip(b'\x00')
        # if sbin has a high bit, add a \x00
        if sbin[0] & 0x80:
            sbin = b'\x00' + sbin
        result += bytes([2, len(sbin)]) + sbin
        return bytes([0x30, len(result)]) + result
    # end::source4[]

    @classmethod
    def parse(cls, signature_bin):
        s = BytesIO(signature_bin)
        compound = s.read(1)[0]
        if compound != 0x30:
            raise SyntaxError("Bad Signature")
        length = s.read(1)[0]
        if length + 2 != len(signature_bin):
            raise SyntaxError("Bad Signature Length")
        marker = s.read(1)[0]
        if marker != 0x02:
            raise SyntaxError("Bad Signature")
        rlength = s.read(1)[0]
        r = int.from_bytes(s.read(rlength), 'big')
        marker = s.read(1)[0]
        if marker != 0x02:
            raise SyntaxError("Bad Signature")
        slength = s.read(1)[0]
        s = int.from_bytes(s.read(slength), 'big')
        if len(signature_bin) != 6 + rlength + slength:
            raise SyntaxError("Signature too long")
        return cls(r, s)


class SignatureTest(TestCase):

    def test_der(self):
        testcases = (
            (1, 2),
            (randint(0, 2**256), randint(0, 2**255)),
            (randint(0, 2**256), randint(0, 2**255)),
        )
        for r, s in testcases:
            sig = Signature(r, s)
            der = sig.der()
            sig2 = Signature.parse(der)
            self.assertEqual(sig2.r, r)
            self.assertEqual(sig2.s, s)


class PrivateKey:

    def __init__(self, secret):
        self.secret = secret
        self.point = secret * G

    def hex(self):
        return '{:x}'.format(self.secret).zfill(64)

    def sign(self, z):
        k = self.deterministic_k(z)
        # r is the x coordinate of the resulting point k*G
        r = (k * G).x.num
        # remember 1/k = pow(k, N-2, N)
        k_inv = pow(k, N - 2, N)
        # s = (z+r*secret) / k
        s = (z + r * self.secret) * k_inv % N
        if s > N / 2:
            s = N - s
        # return an instance of Signature:
        # Signature(r, s)
        return Signature(r, s)

    def deterministic_k(self, z):
        k = b'\x00' * 32
        v = b'\x01' * 32
        if z > N:
            z -= N
        z_bytes = z.to_bytes(32, 'big')
        secret_bytes = self.secret.to_bytes(32, 'big')
        s256 = hashlib.sha256
        k = hmac.new(k, v + b'\x00' + secret_bytes + z_bytes, s256).digest()
        v = hmac.new(k, v, s256).digest()
        k = hmac.new(k, v + b'\x01' + secret_bytes + z_bytes, s256).digest()
        v = hmac.new(k, v, s256).digest()
        while True:
            v = hmac.new(k, v, s256).digest()
            candidate = int.from_bytes(v, 'big')
            if candidate >= 1 and candidate < N:
                return candidate
            k = hmac.new(k, v + b'\x00', s256).digest()
            v = hmac.new(k, v, s256).digest()

    # tag::source6[]
    def wif(self, compressed=True, testnet=False):
        secret_bytes = self.secret.to_bytes(32, 'big')
        if testnet:
            prefix = b'\xef'
        else:
            prefix = b'\x80'
        if compressed:
            suffix = b'\x01'
        else:
            suffix = b''
        return encode_base58_checksum(prefix + secret_bytes + suffix)
    # end::source6[]


class PrivateKeyTest(TestCase):

    def test_sign(self):
        pk = PrivateKey(randint(0, N))
        z = randint(0, 2**256)
        sig = pk.sign(z)
        self.assertTrue(pk.point.verify(z, sig))

    def test_wif(self):
        pk = PrivateKey(2**256 - 2**199)
        expected = 'L5oLkpV3aqBJ4BgssVAsax1iRa77G5CVYnv9adQ6Z87te7TyUdSC'
        self.assertEqual(pk.wif(compressed=True, testnet=False), expected)
        pk = PrivateKey(2**256 - 2**201)
        expected = '93XfLeifX7Jx7n7ELGMAf1SUR6f9kgQs8Xke8WStMwUtrDucMzn'
        self.assertEqual(pk.wif(compressed=False, testnet=True), expected)
        pk = PrivateKey(0x0dba685b4511dbd3d368e5c4358a1277de9486447af7b3604a69b8d9d8b7889d)
        expected = '5HvLFPDVgFZRK9cd4C5jcWki5Skz6fmKqi1GQJf5ZoMofid2Dty'
        self.assertEqual(pk.wif(compressed=False, testnet=False), expected)
        pk = PrivateKey(0x1cca23de92fd1862fb5b76e5f4f50eb082165e5191e116c18ed1a6b24be6a53f)
        expected = 'cNYfWuhDpbNM1JWc3c6JTrtrFVxU4AGhUKgw5f93NP2QaBqmxKkg'
        self.assertEqual(pk.wif(compressed=True, testnet=True), expected)

    ################## ADAPTATION OF PYCOIN CODE FROM HERE:  ########################
    #################################################################################
from binascii import hexlify
from binascii import unhexlify
import six

class BIP32(object):
    """A BIP32 wallet is made up of Wallet nodes.
    A Private node contains both a public and private key, while a public
    node contains only a public key.
    **WARNING**:
    When creating a NEW wallet you MUST back up the private key. If
    you don't then any coins sent to your address will be LOST FOREVER.
    You need to save the private key somewhere. It is OK to just write
    it down on a piece of paper! Don't share this key with anyone!
    >>> my_wallet = Wallet.from_master_secret(
    ...     key='correct horse battery staple')
    >>> private = my_wallet.serialize(private=True)
    >>> private  # doctest: +ELLIPSIS
    u'xprv9s21ZrQH143K2mDJW8vDeFwbyDbFv868mM2Zr87rJSTj8q16Unkaq1pryiV...'
    If you want to use this wallet on your website to accept bitcoin or
    altcoin payments, you should first create a primary child.
    BIP32 Hierarchical Deterministic Wallets are described in this BIP:
    https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki
    """

    def __init__(self,
                 chain_code,
                 depth=0,
                 parent_fingerprint=0,
                 child_number=0,
                 private_exponent=None,
                 private_key=None,
                 public_pair=None,
                 public_key=None,
                 network="bitcoin_testnet"):
        """Construct a new BIP32 compliant wallet.
        You probably don't want to use this init methd. Instead use one
        of the 'from_master_secret' or 'deserialize' cosntructors.
        """

        if (not (private_exponent or private_key) and
                not (public_pair or public_key)):
            raise InsufficientKeyDataError(
                "You must supply one of private_exponent or public_pair")

        network = BIP32.get_network(network)
        self.private_key = None
        self.public_key = None
        if private_key:
            if not isinstance(private_key, PrivateKey):
                raise InvalidPrivateKeyError(
                    "private_key must be of type "
                    "PrivateKey")
            self.private_key = private_key
        elif private_exponent:
            self.private_key = PrivateKey(
                private_exponent, network=network) # I don't know what the heck is Private Exponent

        if public_key:
            """
            if not isinstance(public_key, PublicKey):
                raise InvalidPublicKeyError(
                    "public_key must be of type "
                    "bitmerchant.wallet.keys.PublicKey")
            self.public_key = public_key
        elif public_pair:
            self.public_key = PublicKey.from_public_pair(
                public_pair, network=network)"""
        else:
            self.public_key = PrivateKey(self.private_key) #modified, check later

        if (self.private_key and PrivateKey(self.private_key) !=  #modified, check later. I don't get the logic here
                self.public_key):
            raise KeyMismatchError(
                "Provided private and public values do not match")
        #These h and l I don't have a clue.
        def h(val, hex_len):
            if isinstance(val, six.integer_types):
                return long_to_hex(val, hex_len)
            elif (isinstance(val, six.string_types) or
                    isinstance(val, six.binary_type)) and is_hex_string(val):
                val = ensure_bytes(val)
                if len(val) != hex_len:
                    raise ValueError("Invalid parameter length")
                return val
            else:
                raise ValueError("Invalid parameter type")

        def l(val):
            if isinstance(val, six.integer_types):
                return long_or_int(val)
            elif (isinstance(val, six.string_types) or
                    isinstance(val, six.binary_type)):
                val = ensure_bytes(val)
                if not is_hex_string(val):
                    val = hexlify(val)
                return long_or_int(val, 16)
            else:
                raise ValueError("parameter must be an int or long")

        self.network = Wallet.get_network(network)
        self.depth = l(depth)
        if (isinstance(parent_fingerprint, six.string_types) or
                isinstance(parent_fingerprint, six.binary_type)):
            val = ensure_bytes(parent_fingerprint)
            if val.startswith(b"0x"):
                parent_fingerprint = val[2:]
        self.parent_fingerprint = b"0x" + h(parent_fingerprint, 8)
        self.child_number = l(child_number)
        self.chain_code = h(chain_code, 64)
    """
    def get_private_key_hex(self):
        
        #Get the hex-encoded (I guess SEC1?) representation of the private key.
        #DO NOT share this private key with anyone.
       
        return ensure_bytes(self.private_key.get_key())

    def get_public_key_hex(self, compressed=True):
        #Get the sec1 representation of the public key.
        return ensure_bytes(self.public_key.get_key(compressed))
    """
    """
    @property
    def identifier(self):
    
        #Get the identifier for this node.
        #Extended keys can be identified by the Hash160 (RIPEMD160 after SHA256)
        #of the public key's `key`. This corresponds exactly to the data used in
        #traditional Bitcoin addresses. It is not advised to represent this data
        #in base58 format though, as it may be interpreted as an address that
        #way (and wallet software is not required to accept payment to the chain
        #key itself).
        
        #key = self.get_public_key_hex()
        key = publick.point.sec(True).hex()
        return ensure_bytes(hexlify(hash160(unhexlify(key))))
    """
    @property
    def fingerprint(self):
        #The first 32 bits of the identifier are called the fingerprint.
        # 32 bits == 4 Bytes == 8 hex characters
        return b'0x' + self.identifier[:8]

    def create_new_address_for_user(self, user_id):
        """Create a new bitcoin address to accept payments for a User.
        This is a convenience wrapper around `get_child` that helps you do
        the right thing. This method always creates a public, non-prime
        address that can be generated from a BIP32 public key on an
        insecure server."""
        max_id = 0x80000000
        if user_id < 0 or user_id > max_id:
            raise ValueError(
                "Invalid UserID. Must be between 0 and %s" % max_id)
        return self.get_child(user_id, is_prime=False, as_private=False)

    def get_child_for_path(self, path):
        """Get a child for a given path.
        Rather than repeated calls to get_child, children can be found
        by a derivation path. Paths look like:
            m/0/1'/10
        Which is the same as
            self.get_child(0).get_child(-1).get_child(10)
        Or, in other words, the 10th publicly derived child of the 1st
        privately derived child of the 0th publicly derived child of master.
        You can use either ' or p to denote a prime (that is, privately
        derived) child.
        A child that has had its private key stripped can be requested by
        either passing a capital M or appending '.pub' to the end of the path.
        These three paths all give the same child that has had its private
        key scrubbed:
            M/0/1
            m/0/1.pub
            M/0/1.pub
        """
        path = ensure_str(path)

        if not path:
            raise InvalidPathError("%s is not a valid path" % path)

        # Figure out public/private derivation
        as_private = True
        if path.startswith("M"):
            as_private = False
        if path.endswith(".pub"):
            as_private = False
            path = path[:-4]

        parts = path.split("/")
        if len(parts) == 0:
            raise InvalidPathError()

        child = self
        for part in parts:
            if part.lower() == "m":
                continue
            is_prime = None  # Let primeness be figured out by the child number
            if part[-1] in "'p":
                is_prime = True
                part = part.replace("'", "").replace("p", "")
            try:
                child_number = long_or_int(part)
            except ValueError:
                raise InvalidPathError("%s is not a valid path" % path)
            child = child.get_child(child_number, is_prime)
        if not as_private:
            return child.public_copy()
        return child

    #@memoize
    def get_child(self, child_number, is_prime=None, as_private=True):
        """Derive a child key.
        :param child_number: The number of the child key to compute
        :type child_number: int
        :param is_prime: If True, the child is calculated via private
            derivation. If False, then public derivation is used. If None,
            then it is figured out from the value of child_number.
        :type is_prime: bool, defaults to None
        :param as_private: If True, strips private key from the result.
            Defaults to False. If there is no private key present, this is
            ignored.
        :type as_private: bool
        Positive child_numbers (less than 2,147,483,648) produce publicly
        derived children.
        Negative numbers (greater than -2,147,483,648) uses private derivation.
        NOTE: Python can't do -0, so if you want the privately derived 0th
        child you need to manually set is_prime=True.
        NOTE: negative numbered children are provided as a convenience
        because nobody wants to remember the above numbers. Negative numbers
        are considered 'prime children', which is described in the BIP32 spec
        as a leading 1 in a 32 bit unsigned int.
        This derivation is fully described at
        https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#child-key-derivation-functions  # nopep8
        """
        boundary = 0x80000000

        if abs(child_number) >= boundary:
            raise ValueError("Invalid child number %s" % child_number)

        # If is_prime isn't set, then we can infer it from the child_number
        if is_prime is None:
            # Prime children are either < 0 or > 0x80000000
            if child_number < 0:
                child_number = abs(child_number)
                is_prime = True
            elif child_number >= boundary:
                child_number -= boundary
                is_prime = True
            else:
                is_prime = False
        else:
            # Otherwise is_prime is set so the child_number should be between
            # 0 and 0x80000000
            if child_number < 0 or child_number >= boundary:
                raise ValueError(
                    "Invalid child number. Must be between 0 and %s" %
                    boundary)

        if not self.private_key and is_prime:
            raise ValueError(
                "Cannot compute a prime child without a private key")

        if is_prime:
            # Even though we take child_number as an int < boundary, the
            # internal derivation needs it to be the larger number.
            child_number = child_number + boundary
        child_number_hex = long_to_hex(child_number, 8)

        if is_prime:
            # Let data = concat(0x00, self.key, child_number)
            data = b'00' + self.private_key.get_key()
        else:
            data = self.get_public_key_hex()
        data += child_number_hex

        # Compute a 64 Byte I that is the HMAC-SHA512, using self.chain_code
        # as the seed, and data as the message.
        I = hmac.new(
            unhexlify(self.chain_code),
            msg=unhexlify(data),
            digestmod=sha512).digest()
        # Split I into its 32 Byte components.
        I_L, I_R = I[:32], I[32:]

        if long_or_int(hexlify(I_L), 16) >= SECP256k1.order:
            raise InvalidPrivateKeyError("The derived key is too large.")

        c_i = hexlify(I_R)
        private_exponent = None
        public_pair = None
        if self.private_key:
            # Use private information for derivation
            # I_L is added to the current key's secret exponent (mod n), where
            # n is the order of the ECDSA curve in use.
            private_exponent = (
                (long_or_int(hexlify(I_L), 16) +
                 long_or_int(self.private_key.get_key(), 16))
                % SECP256k1.order)
            # I_R is the child's chain code
        else:
            # Only use public information for this derivation
            g = SECP256k1.generator
            I_L_long = long_or_int(hexlify(I_L), 16)
            point = (_ECDSA_Public_key(g, g * I_L_long).point +
                     self.public_key.to_point())
            # I_R is the child's chain code
            public_pair = PublicPair(point.x(), point.y())

        child = self.__class__(
            chain_code=c_i,
            depth=self.depth + 1,  # we have to go deeper...
            parent_fingerprint=self.fingerprint,
            child_number=child_number_hex,
            private_exponent=private_exponent,
            public_pair=public_pair,
            network=self.network)
        if child.public_key.to_point() == INFINITY:
            raise InfinityPointException("The point at infinity is invalid.")
        if not as_private:
            return child.public_copy()
        return child

    def public_copy(self):
        """Clone this wallet and strip it of its private information."""
        return self.__class__(
            chain_code=self.chain_code,
            depth=self.depth,
            parent_fingerprint=self.parent_fingerprint,
            child_number=self.child_number,
            public_pair=self.public_key.to_public_pair(),
            network=self.network)

    def crack_private_key(self, child_private_key):
        """Crack the parent private key given a child private key.
        BIP32 has a vulnerability/feature that allows you to recover the
        master private key if you're given a master public key and any of its
        publicly-derived child private keys. This is a pretty serious security
        vulnerability that looks as innocuous as this:
        >>> w = Wallet.new_random_wallet()
        >>> child = w.get_child(0, is_prime=False)
        >>> w_pub = w.public_copy()
        >>> assert w_pub.private_key is None
        >>> master_public_key = w_pub.serialize_b58(private=False)
        >>> # Now you put master_public_key on your website
        >>> # and give somebody a private key
        >>> public_master = Wallet.deserialize(master_public_key)
        >>> cracked_private_master = public_master.crack_private_key(child)
        >>> assert w == cracked_private_master  # :(
        Implementation details from http://bitcoinmagazine.com/8396/deterministic-wallets-advantages-flaw/  # nopep8
        """
        if self.private_key:
            raise AssertionError("You already know the private key")
        if child_private_key.parent_fingerprint != self.fingerprint:
            raise ValueError("This is not a valid child")
        if child_private_key.child_number >= 0x80000000:
            raise ValueError(
                "Cannot crack private keys from private derivation")

        # Duplicate the public child derivation
        child_number_hex = long_to_hex(child_private_key.child_number, 8)
        data = self.get_public_key_hex() + child_number_hex
        I = hmac.new(
            unhexlify(self.chain_code),
            msg=unhexlify(data),
            digestmod=sha512).digest()
        I_L, I_R = I[:32], I[32:]
        # Public derivation is the same as private derivation plus some offset
        # knowing the child's private key allows us to find this offset just
        # by subtracting the child's private key from the parent I_L data
        privkey = PrivateKey(long_or_int(hexlify(I_L), 16),
                             network=self.network)
        parent_private_key = child_private_key.private_key - privkey
        return self.__class__(
            chain_code=self.chain_code,
            depth=self.depth,
            parent_fingerprint=self.parent_fingerprint,
            child_number=self.child_number,
            private_key=parent_private_key,
            network=self.network)

    def export_to_wif(self):
        """Export a key to WIF.
        See https://en.bitcoin.it/wiki/Wallet_import_format for a full
        description.
        """
        # Add the network byte, creating the "extended key"
        extended_key_hex = self.private_key.get_extended_key()
        # BIP32 wallets have a trailing \01 byte
        extended_key_bytes = unhexlify(extended_key_hex) + b'\01'
        # And return the base58-encoded result with a checksum
        return base58.b58encode_check(extended_key_bytes)

    def serialize(self, private=True):
        """Serialize this key.
        :param private: Whether or not the serialized key should contain
            private information. Set to False for a public-only representation
            that cannot spend funds but can create children. You want
            private=False if you are, for example, running an e-commerce
            website and want to accept bitcoin payments. See the README
            for more information.
        :type private: bool, defaults to True
        See the spec in `deserialize` for more details.
        """
        if private and not self.private_key:
            raise ValueError("Cannot serialize a public key as private")

        if private:
            network_version = long_to_hex(
                self.network.EXT_SECRET_KEY, 8)
        else:
            network_version = long_to_hex(
                self.network.EXT_PUBLIC_KEY, 8)
        depth = long_to_hex(self.depth, 2)
        parent_fingerprint = self.parent_fingerprint[2:]  # strip leading 0x
        child_number = long_to_hex(self.child_number, 8)
        chain_code = self.chain_code
        ret = (network_version + depth + parent_fingerprint + child_number +
               chain_code)
        # Private and public serializations are slightly different
        if private:
            ret += b'00' + self.private_key.get_key()
        else:
            ret += self.get_public_key_hex(compressed=True)
        return ensure_bytes(ret.lower())

    def serialize_b58(self, private=True):
        """Encode the serialized node in base58."""
        return ensure_str(
            base58.b58encode_check(unhexlify(self.serialize(private))))

    def to_address(self):
        """Create a public address from this Wallet.
        Public addresses can accept payments.
        https://en.bitcoin.it/wiki/Technical_background_of_Bitcoin_addresses
        """
        key = unhexlify(self.get_public_key_hex())
        # First get the hash160 of the key
        hash160_bytes = hash160(key)
        # Prepend the network address byte
        network_hash160_bytes = \
            chr_py2(self.network.PUBKEY_ADDRESS) + hash160_bytes
        # Return a base58 encoded address with a checksum
        return ensure_str(base58.b58encode_check(network_hash160_bytes))

    @classmethod #@memoize
    def deserialize(cls, key, network="bitcoin_testnet"):
        """Load the ExtendedBip32Key from a hex key.
        The key consists of
            * 4 byte version bytes (network key)
            * 1 byte depth:
                - 0x00 for master nodes,
                - 0x01 for level-1 descendants, ....
            * 4 byte fingerprint of the parent's key (0x00000000 if master key)
            * 4 byte child number. This is the number i in x_i = x_{par}/i,
              with x_i the key being serialized. This is encoded in MSB order.
              (0x00000000 if master key)
            * 32 bytes: the chain code
            * 33 bytes: the public key or private key data
              (0x02 + X or 0x03 + X for public keys, 0x00 + k for private keys)
              (Note that this also supports 0x04 + X + Y uncompressed points,
              but this is totally non-standard and this library won't even
              generate such data.)
        """
        network = Wallet.get_network(network)

        if len(key) in [78, (78 + 32)]:
            # we have a byte array, so pass
            pass
        else:
            key = ensure_bytes(key)
            if len(key) in [78 * 2, (78 + 32) * 2]:
                # we have a hexlified non-base58 key, continue!
                key = unhexlify(key)
            elif len(key) == 111:
                # We have a base58 encoded string
                key = base58.b58decode_check(key)
        # Now that we double checkd the values, convert back to bytes because
        # they're easier to slice
        version, depth, parent_fingerprint, child, chain_code, key_data = (
            key[:4], key[4], key[5:9], key[9:13], key[13:45], key[45:])

        version_long = long_or_int(hexlify(version), 16)
        exponent = None
        pubkey = None
        point_type = key_data[0]
        if not isinstance(point_type, six.integer_types):
            point_type = ord(point_type)
        if point_type == 0:
            # Private key
            if version_long != network.EXT_SECRET_KEY:
                raise incompatible_network_exception_factory(
                    network.NAME, network.EXT_SECRET_KEY,
                    version)
            exponent = key_data[1:]
        elif point_type in [2, 3, 4]:
            # Compressed public coordinates
            if version_long != network.EXT_PUBLIC_KEY:
                raise incompatible_network_exception_factory(
                    network.NAME, network.EXT_PUBLIC_KEY,
                    version)
            pubkey = PublicKey.from_hex_key(key_data, network=network)
            # Even though this was generated from a compressed pubkey, we
            # want to store it as an uncompressed pubkey
            pubkey.compressed = False
        else:
            raise ValueError("Invalid key_data prefix, got %s" % point_type)

        def l(byte_seq):
            if byte_seq is None:
                return byte_seq
            elif isinstance(byte_seq, six.integer_types):
                return byte_seq
            return long_or_int(hexlify(byte_seq), 16)

        return cls(depth=l(depth),
                   parent_fingerprint=l(parent_fingerprint),
                   child_number=l(child),
                   chain_code=l(chain_code),
                   private_exponent=l(exponent),
                   public_key=pubkey,
                   network=network)

    @classmethod
    def from_master_secret(cls, seed, network="bitcoin_testnet"):
        """Generate a new PrivateKey from a secret key.
        :param seed: The key to use to generate this wallet. It may be a long
            string. Do not use a phrase from a book or song, as that will
            be guessed and is not secure. My advice is to not supply this
            argument and let me generate a new random key for you.
        See https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#Serialization_format  # nopep8
        """
        network = Wallet.get_network(network)
        seed = ensure_bytes(seed)
        # Given a seed S of at least 128 bits, but 256 is advised
        # Calculate I = HMAC-SHA512(key="Bitcoin seed", msg=S)
        I = hmac.new(b"Bitcoin seed", msg=seed, digestmod=sha512).digest()
        # Split I into two 32-byte sequences, IL and IR.
        I_L, I_R = I[:32], I[32:]
        # Use IL as master secret key, and IR as master chain code.
        return cls(private_exponent=long_or_int(hexlify(I_L), 16),
                   chain_code=long_or_int(hexlify(I_R), 16),
                   network=network)

    @classmethod
    def from_master_secret_slow(cls, password, network="BTCTEST"):
        """
        Generate a new key from a password using 50,000 rounds of HMAC-SHA256.
        This should generate the same result as bip32.org.
        WARNING: The security of this method has not been evaluated.
        """
        # Make sure the password string is bytes
        key = ensure_bytes(password)
        data = unhexlify(b"0" * 64)  # 256-bit 0
        for i in range(50000):
            data = hmac.new(key, msg=data, digestmod=sha256).digest()
        return cls.from_master_secret(data, network)

    def __eq__(self, other):
        attrs = [
            'chain_code',
            'depth',
            'parent_fingerprint',
            'child_number',
            'private_key',
            'public_key',
            'network',
        ]
        return other and all(
            getattr(self, attr) == getattr(other, attr) for attr in attrs)

    def __ne__(self, other):
        return not self == other

    __hash__ = object.__hash__

    @classmethod
    def get_network(self, network):
        # returns a network class object

        response = None
        if network == "bitcoin_testnet" or network == "BTCTEST":
            response = BitcoinTestNet
        elif network == "bitcoin" or network == "BTC":
            response = BitcoinMainNet
        elif network == "dogecoin" or network == "DOGE":
            response = DogecoinMainNet
        elif network == "dogecoin_testnet" or network == "DOGETEST":
            response = DogecoinTestNet
        elif network == "litecoin" or network == "LTC":
            response = LitecoinMainNet
        elif network == "litecoin_testnet" or network == "LTCTEST":
            response = LitecoinTestNet
        elif network == "bitcoin_cash" or network == "BCH":
            response = BitcoinCashMainNet
        elif network == "bitcoin_gold" or network == "BTG":
            response = BitcoinGoldMainNet
        elif network == "dash" or network == "DASH":
            response = DashMainNet
        elif network == 'dash_testnet' or network == 'DASHTEST':
            response = DashTestNet
        elif network == 'omni' or network == 'OMNI':
            response = OmniMainNet
        elif network == 'omni_testnet' or network == 'OMNI_TESTNET':
            response = OmniTestNet
        elif network == 'feathercoin' or network == 'FTC':
            response = FeathercoinMainNet
        elif network == "qtum" or network == "QTUM":
            response = QtumMainNet
        elif network == 'qtum_testnet' or network == 'QTUMTEST':
            response = QtumTestNet
        else:
            response = network
        return response

    @classmethod
    def new_random_wallet(cls, user_entropy=None, network="BTCTEST"):
        """
        Generate a new wallet using a randomly generated 512 bit seed.
        Args:
            user_entropy: Optional user-supplied entropy which is combined
                combined with the random seed, to help counteract compromised
                PRNGs.
        You are encouraged to add an optional `user_entropy` string to protect
        against a compromised CSPRNG. This will be combined with the output
        from the CSPRNG. Note that if you do supply this value it only adds
        additional entropy and will not be sufficient to recover the random
        wallet. If you're even saving `user_entropy` at all, you're doing it
        wrong.
        """
        seed = str(urandom(64))  # 512/8
        # weak extra protection inspired by pybitcointools implementation:
        seed += str(int(time.time()*10**6))
        if user_entropy:
            user_entropy = str(user_entropy)  # allow for int/long
            seed += user_entropy
        return cls.from_master_secret(seed, network=network)


class InvalidPathError(Exception):
    pass


class InsufficientKeyDataError(ValueError):
    pass


class InvalidPrivateKeyError(ValueError):
    pass


class InvalidPublicKeyError(ValueError):
    pass


class KeyMismatchError(ValueError):
    pass


class InfinityPointException(Exception):
    pass
    
################## END OF ADAPTATION OF PYCOIN CODE.  ########################
