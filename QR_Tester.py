from main import make

# Crée un objet Qr Code
# Ajoute les données à ce Qr Code
# Le Transforme en image

#qr = make('perso.esiee.fr/~vigierj')
qr = make('Hello, world!')
# qr = make('123456')


qr.save('qr_img.png')
print("qr code créé.")