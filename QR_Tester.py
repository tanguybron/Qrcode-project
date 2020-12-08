from main import make

# Crée un objet Qr Code
# Ajoute les données à ce Qr Code
# Le Transforme en image
qr = make('ok')

qr.save('qr_img.png')
print("qr code créé.")