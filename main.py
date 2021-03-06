#from qrcode import constants, exceptions, util
import util,constants,exceptions
#from qrcode.image.base import BaseImage
from image.base import BaseImage

import six
from bisect import bisect_left

## string est la chaine de caractère que nous prenons comme argument.
def make(string):
    qr = QRCode()
    qr.add_data(string)
    print("ok")
    return qr.make_image()


def _check_version(version):
    #print(version)
    if version < 1 or version > 40:
        raise ValueError(
            "Invalid version (was %s, expected 1 to 40)" % version)


def _check_box_size(size):
    if int(size) <= 0:
        raise ValueError(
            "Invalid box size (was %s, expected larger than 0)" % size)


def _check_mask_pattern(mask_pattern):
    if mask_pattern is None:
        return
    if not isinstance(mask_pattern, int):
        raise TypeError(
            "Invalid mask pattern (was %s, expected int)" % type(mask_pattern))
    if mask_pattern < 0 or mask_pattern > 7:
        raise ValueError(
            "Mask pattern should be in range(8) (got %s)" % mask_pattern)

class QRCode:

    # Attribut : 
    # version
    # error_correction
    # box_size & border
    # image_factory
    # mask_pattern

    def __init__(self):
        #on utilise la version 2 pour avoir 25 modules
        self.version = 2
        self.error_correction = 0
        self.box_size = 10
        self.border = 4
        self.image_factory = None
        self.mask_pattern = None
        self.clear()

    def clear(self):
        """
        Reset the internal data.
        """
        self.modules = None
        self.modules_count = 0
        self.data_cache = None
        self.data_list = []

    def add_data(self, string):
        """
        Add data to this QR Code.
        """
        
        #util.QRData transforme la chaine de caractère de départ en type byte
        self.data_list.append(util.QRData(string))
        #self.data_list.append(string.encode('utf8'))
        print(self.data_list)
        self.data_cache = None

    def make(self, fit=True):
        """
        Compile the data into a QR Code array.

        :param fit: If ``True`` (or if a size has not been provided), find the
            best fit for the data to avoid data overflow errors.
        """
        # if fit or (self.version is None):
        #     self.best_fit(start=self.version)
        if self.mask_pattern is None:
            self.makeImpl(False, self.best_mask_pattern())
        else:
            self.makeImpl(False, self.mask_pattern)

    def makeImpl(self, test, mask_pattern):
        # _check_version(self.version)
        # self.modules_count est le nombre de modules (on utilise du 25x25 ici)
        # self.modules_count = 25
        self.modules_count = self.version * 4 + 17
        # met tous les modules à None
        self.modules = [None] * self.modules_count

        for row in range(self.modules_count):

            self.modules[row] = [None] * self.modules_count

            for col in range(self.modules_count):
                self.modules[row][col] = None   # (col + row) % 3

        # mets les 3 carrés dans les coins
        self.setup_position_probe_pattern(0, 0)
        self.setup_position_probe_pattern(self.modules_count - 7, 0)
        self.setup_position_probe_pattern(0, self.modules_count - 7)


        # ==================================================== #
        ## comprendre pourquoi c'est utile (sans cela, le qr code est créé mais illisible)
        self.setup_position_adjust_pattern()
        self.setup_timing_pattern()
        self.setup_type_info(test, mask_pattern)
        # à voir Jojo ou Tristan
        # ==================================================== #
        

        if self.data_cache is None:
            ## create data ?
            self.data_cache = util.create_data(
                self.version, self.error_correction, self.data_list)
            print(self.data_cache)
        self.map_data(self.data_cache, mask_pattern)





    ## Dessine les deux carrés imbriqués qui servent à délimiter le Qr code.
    ## Il commence à partir du coin supérieur gauche (dont il faut renseigner la position dans row et col en argument)
    def setup_position_probe_pattern(self, row, col):
        for r in range(-1, 8):

            if row + r <= -1 or self.modules_count <= row + r:
                continue

            for c in range(-1, 8):

                if col + c <= -1 or self.modules_count <= col + c:
                    continue

                if (0 <= r and r <= 6 and (c == 0 or c == 6)
                        or (0 <= c and c <= 6 and (r == 0 or r == 6))
                        or (2 <= r and r <= 4 and 2 <= c and c <= 4)):
                    self.modules[row + r][col + c] = True
                else:
                    self.modules[row + r][col + c] = False


    def best_mask_pattern(self):
        """
        Find the most efficient mask pattern.
        """
        min_lost_point = 0
        pattern = 0
        for i in range(8):
            ## fait le qr code (la map et les données)
            self.makeImpl(True, i)
            lost_point = util.lost_point(self.modules)
            #print(lost_point)
            if i == 0 or min_lost_point > lost_point:
                min_lost_point = lost_point
                pattern = i

        return pattern

    def print_tty(self, out=None):
        """
        Output the QR Code only using TTY colors.

        If the data has not been compiled yet, make it first.
        """
        if out is None:
            import sys
            out = sys.stdout

        if not out.isatty():
            raise OSError("Not a tty")

        if self.data_cache is None:
            self.make()

        modcount = self.modules_count
        out.write("\x1b[1;47m" + (" " * (modcount * 2 + 4)) + "\x1b[0m\n")
        for r in range(modcount):
            out.write("\x1b[1;47m  \x1b[40m")
            for c in range(modcount):
                if self.modules[r][c]:
                    out.write("  ")
                else:
                    out.write("\x1b[1;47m  \x1b[40m")
            out.write("\x1b[1;47m  \x1b[0m\n")
        out.write("\x1b[1;47m" + (" " * (modcount * 2 + 4)) + "\x1b[0m\n")
        out.flush()

    def print_ascii(self, out=None, tty=False, invert=False):
        """
        Output the QR Code using ASCII characters.

        :param tty: use fixed TTY color codes (forces invert=True)
        :param invert: invert the ASCII characters (solid <-> transparent)
        """
        if out is None:
            import sys
            if sys.version_info < (2, 7):
                # On Python versions 2.6 and earlier, stdout tries to encode
                # strings using ASCII rather than stdout.encoding, so use this
                # workaround.
                import codecs
                out = codecs.getwriter(sys.stdout.encoding)(sys.stdout)
            else:
                out = sys.stdout

        if tty and not out.isatty():
            raise OSError("Not a tty")

        if self.data_cache is None:
            self.make()

        modcount = self.modules_count
        codes = [six.int2byte(code).decode('cp437')
                 for code in (255, 223, 220, 219)]
        if tty:
            invert = True
        if invert:
            codes.reverse()

        def get_module(x, y):
            if (invert and self.border and
                    max(x, y) >= modcount+self.border):
                return 1
            if min(x, y) < 0 or max(x, y) >= modcount:
                return 0
            return self.modules[x][y]

        for r in range(-self.border, modcount+self.border, 2):
            if tty:
                if not invert or r < modcount+self.border-1:
                    out.write('\x1b[48;5;232m')   # Background black
                out.write('\x1b[38;5;255m')   # Foreground white
            for c in range(-self.border, modcount+self.border):
                pos = get_module(r, c) + (get_module(r+1, c) << 1)
                out.write(codes[pos])
            if tty:
                out.write('\x1b[0m')
            out.write('\n')
        out.flush()

    #On enlève le **kwargs
    def make_image(self, image_factory=None):
        """
        Make an image from the QR Code data.

        If the data has not been compiled yet, make it first.
        """
        # vérifie juste si la box_size est valide
        _check_box_size(self.box_size)

        # Si tout va bien on entre dans le if.
        if self.data_cache is None:
            self.make()

        image_factory = self.image_factory
        if image_factory is None:
            # Use PIL by default
            ## Utilise la classe PilImage écritent dans ./images/pil.py
            from qrcode.image.pil import PilImage
            image_factory = PilImage
        ## Ici, l'image est vide. On a rien mit dedans.

        # On met l'image à la bonne taille : 
        # on prend en compte le nombre de modules (ici 25), la taille de l'image, et la bordure
        im = image_factory(
            self.border, self.modules_count, self.box_size) # ---- Comprendre exactement comment fonctionne ces deux lignes ----
        #print(self.modules)
        # place les petits carrés du qr code (l'information)
        ## On place les carrés en les parcourant ligne par ligne

        for r in range(self.modules_count):
            for c in range(self.modules_count):
                # Si module est false le carré reste blanc, sinon on le colorie
                if self.modules[r][c]:
                    # drawrect dessine un rectangle : la fonction a été écrite dans la classe PilImage dans ./images/pil.py
                    im.drawrect(r, c)
        return im

    def setup_timing_pattern(self):
        for r in range(8, self.modules_count - 8):
            if self.modules[r][6] is not None:
                continue
            self.modules[r][6] = (r % 2 == 0)

        for c in range(8, self.modules_count - 8):
            if self.modules[6][c] is not None:
                continue
            self.modules[6][c] = (c % 2 == 0)

    def setup_position_adjust_pattern(self):
        #pos = [6,18]
        #pos = util.pattern_position(self.version)
        
        pos = [6,18]
        for i in range(len(pos)):

            for j in range(len(pos)):

                row = pos[i]
                col = pos[j]

                if self.modules[row][col] is not None:
                    continue

                for r in range(-2, 3):

                    for c in range(-2, 3):

                        if (r == -2 or r == 2 or c == -2 or c == 2 or
                                (r == 0 and c == 0)):
                            self.modules[row + r][col + c] = True
                        else:
                            self.modules[row + r][col + c] = False

    def setup_type_number(self, test):
        bits = util.BCH_type_number(self.version)

        for i in range(18):
            mod = (not test and ((bits >> i) & 1) == 1)
            self.modules[i // 3][i % 3 + self.modules_count - 8 - 3] = mod

        for i in range(18):
            mod = (not test and ((bits >> i) & 1) == 1)
            self.modules[i % 3 + self.modules_count - 8 - 3][i // 3] = mod

    def setup_type_info(self, test, mask_pattern):
        data = (self.error_correction << 3) | mask_pattern
        bits = util.BCH_type_info(data)

        # vertical
        for i in range(15):

            mod = (not test and ((bits >> i) & 1) == 1)

            if i < 6:
                self.modules[i][8] = mod
            elif i < 8:
                self.modules[i + 1][8] = mod
            else:
                self.modules[self.modules_count - 15 + i][8] = mod

        # horizontal
        for i in range(15):

            mod = (not test and ((bits >> i) & 1) == 1)

            if i < 8:
                self.modules[8][self.modules_count - i - 1] = mod
            elif i < 9:
                self.modules[8][15 - i - 1 + 1] = mod
            else:
                self.modules[8][15 - i - 1] = mod

        # fixed module
        self.modules[self.modules_count - 8][8] = (not test)

    def map_data(self, data, mask_pattern):
        inc = -1
        row = self.modules_count - 1
        bitIndex = 7
        byteIndex = 0

        mask_func = util.mask_func(mask_pattern)
        data_len = len(data)

        #print(self.modules)

        for col in range(self.modules_count - 1, 0, -2):

            if col <= 6:
                col -= 1

            col_range = (col, col-1)
            while True:

                for c in col_range:

                    if self.modules[row][c] is None:

                        dark = False

                        if byteIndex < data_len:
                            dark = (((data[byteIndex] >> bitIndex) & 1) == 1)

                        if mask_func(row, c):
                            dark = not dark

                        self.modules[row][c] = dark
                        bitIndex -= 1

                        if bitIndex == -1:
                            byteIndex += 1
                            bitIndex = 7

                row += inc

                if row < 0 or self.modules_count <= row:
                    row -= inc
                    inc = -inc
                    break

    # def get_matrix(self):
    #     """
    #     Return the QR Code as a multidimensonal array, including the border.

    #     To return the array without a border, set ``self.border`` to 0 first.
    #     """
    #     if self.data_cache is None:
    #         self.make()

    #     if not self.border:
    #         return self.modules

    #     width = len(self.modules) + self.border*2
    #     code = [[False]*width] * self.border
    #     x_border = [False]*self.border
    #     for module in self.modules:
    #         code.append(x_border + module + x_border)
    #     code += [[False]*width] * self.border

    #     return code