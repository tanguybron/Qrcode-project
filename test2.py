import qrcode

qr = qrcode.make('perso.esiee.fr/~vigierj')
qr.save('qr_img_test.png')