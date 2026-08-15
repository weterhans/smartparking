x = [4.17, 1.57, 0.399, 0.444, 29.3, 0.810, 0.848, 0.540]
x_min = [3.20, 1.28, 0.251, 0.23, 14.6, 0.51, 0.39, 0.14]
x_max = [5.46, 2.05, 0.460, 1.03, 58.0, 0.96, 1.00, 0.79]
with open("norm_out.txt", "w") as f:
    for i in range(8):
        norm = (x[i] - x_min[i]) / (x_max[i] - x_min[i])
        f.write(f'Fitur {i+1}: ({x[i]} - {x_min[i]}) / ({x_max[i]} - {x_min[i]}) = {x[i]-x_min[i]:.3f} / {x_max[i]-x_min[i]:.3f} = {norm:.3f}\n')
