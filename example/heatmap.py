# """
# congestion_heatmap.py
# ---------------------
# Draw a contour-style congestion heatmap that
#   • uses square cells (same size in X & Y)
#   • smooths with an isotropic Gaussian kernel
#   • fades to white as density → 0
#   • keeps a true-shape (equal-aspect) display
# """
#
# import json
# import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.colors import ListedColormap
#
# # ---------------------------------------------------------------------------
# # 0.  Optional: blur helper --------------------------------------------------
# try:
#     from scipy.ndimage import gaussian_filter
#     has_scipy = True
# except ImportError:
#     has_scipy = False
#     print("[info] SciPy not found → skipping Gaussian blur")
#
# # ---------------------------------------------------------------------------
# # 1.  Load coordinates -------------------------------------------------------
# #     Adjust the file name/path as needed
# with open("../libs/recordings/cmine_data.json") as f:
#     sim = json.load(f)
#
# xs, ys = zip(*[
#     feat["geometry"]["coordinates"]
#     for msg in sim["messages"]
#     for feat in msg["data"]["features"]
# ])
# xs, ys = np.array(xs), np.array(ys)
#
# # ---------------------------------------------------------------------------
# # 2.  Build a square-cell 2-D histogram --------------------------------------
# cell = 15.0                                  # ← desired cell side length (units = your coords)
# nx   = int(np.ceil((xs.max() - xs.min()) / cell))
# ny   = int(np.ceil((ys.max() - ys.min()) / cell))
#
# counts, xedges, yedges = np.histogram2d(xs, ys, bins=[nx, ny])
#
# # Optional: isotropic blur (sigma in *cells*)
# if has_scipy:
#     counts = gaussian_filter(counts, sigma=3)
#
# # ---------------------------------------------------------------------------
# # 3.  Make a “fade-to-white” colormap ----------------------------------------
# base    = plt.cm.get_cmap('viridis', 256)    # change base map if you like
# newcols = base(np.linspace(0, 1, 256))
#
# Nfade   = 60                                 # how many lowest colours fade to white
# white   = np.array([1, 1, 1, 1])
# for i in range(Nfade):
#     α = i / float(Nfade)                     # 0 → white … 1 → first colour
#     newcols[i] = white * (1 - α) + newcols[Nfade] * α
#
# fade_cmap = ListedColormap(newcols)
#
# # ---------------------------------------------------------------------------
# # 4.  Meshgrid for contourf --------------------------------------------------
# xc = (xedges[:-1] + xedges[1:]) / 2
# yc = (yedges[:-1] + yedges[1:]) / 2
# X, Y = np.meshgrid(xc, yc, indexing='ij')
#
# # ---------------------------------------------------------------------------
# # ax.set_xlim(xs.min() - m * np.ptp(xs), xs.max() + m * np.ptp(xs))
# # ax.set_ylim(ys.min() - m * np.ptp(ys), ys.max() + m * np.ptp(ys))
#
# # ---------------------------------------------------------------------------
# # 5.  Plot -------------------------------------------------------------------
# fig, ax = plt.subplots(figsize=(10, 5))
#
# levels  = 40                                  # smoother gradient
# cs      = ax.contourf(X, Y, counts, levels=levels, cmap=fade_cmap)
#
# # 5 % frame margin
# m = 0.05
# ax.set_xlim(xs.min() - m * np.ptp(xs), xs.max() + m * np.ptp(xs))
# ax.set_ylim(ys.min() - m * np.ptp(ys), ys.max() + m * np.ptp(ys))
#
#
# # Keep true shape
# ax.set_aspect('equal', adjustable='box')
#
# # ---------------------------------------------------------------------------
# # **Create a colour-bar axes that matches the plot height**
# from mpl_toolkits.axes_grid1.inset_locator import inset_axes
#
# cax = inset_axes(
#     ax,                       # parent axes
#     width="3%",               # bar width (as % of ax width or fixed e.g. "30%")
#     height="100%",            # bar height = 100 % of Axes height
#     loc="lower left",
#     bbox_to_anchor=(1.02, 0., 1, 1),  # place just outside the Axes on the right
#     bbox_transform=ax.transAxes,
#     borderpad=0,
# )
#
# fig.colorbar(cs, cax=cax, label='Density (counts per cell)')
#
# # ---------------------------------------------------------------------------
# # Labels & title -------------------------------------------------------------
# ax.set_title('Congestion Heatmap – Contour (square cells, fades to white)')
# ax.set_xlabel('X coordinate')
# ax.set_ylabel('Y coordinate')
#
# # ax.tight_layout()
# plt.show()


import json, numpy as np, matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
try:
    from scipy.ndimage import gaussian_filter
    has_scipy = True
except ImportError:
    has_scipy = False

# ---------------------------------------------------------------------------
# 1. read coordinates --------------------------------------------------------
with open("../libs/recordings/cmine_data2.json") as f:
    sim = json.load(f)

xs, ys = zip(*[
    feat["geometry"]["coordinates"]
    for msg in sim["messages"]
    for feat in msg["data"]["features"]
    if feat["geometry"]["type"] == "Point"
])

speeds = [feat["properties"]['speed']
          for msg in sim["messages"]
          for feat in msg["data"]["features"]
          if feat["geometry"]["type"] == "Point"
          ]

xs, ys, speeds = np.asarray(xs), np.asarray(ys), np.asarray(speeds)

# remove offset
xs = xs - xs.min()
ys = ys - ys.min()

# 3. fade-to-white cmap -------------------------------------------------------
base    = plt.cm.get_cmap('viridis', 256)
newcols = base(np.linspace(0, 1, 256))
Nfade   = 60
white   = np.ones(4)
for i in range(Nfade):
    α = i / float(Nfade)
    newcols[i] = white * (1 - α) + newcols[Nfade] * α
fade_cmap = ListedColormap(newcols)

# ---------------------------------------------------------------------------
# 2. decide cell size + *physical* margin ------------------------------------
cell        = 60.0      # square-cell side length (units = your coords)
margin_frac = 0.05      # 5 % of each span → physical margin distance
mx = margin_frac * np.ptp(xs)
my = margin_frac * np.ptp(ys)

x_min, x_max = xs.min() - mx, xs.max() + mx
y_min, y_max = ys.min() - my, ys.max() + my

nx = int(np.ceil((x_max - x_min) / cell))
ny = int(np.ceil((y_max - y_min) / cell))

# re-snap the outer edges so every bin is exactly `cell`
x_max = x_min + nx * cell
y_max = y_min + ny * cell

# histogram over the *expanded* range
counts, xedges, yedges = np.histogram2d(
    xs, ys,
    bins=[nx, ny],
    range=[[x_min, x_max], [y_min, y_max]],
)

total, _, _ = np.histogram2d(xs, ys, bins=[nx, ny],
                             range=[[x_min, x_max], [y_min, y_max]])


# ----------------
V0 = 2.0 / 3.6  # 5 km/h in m/s
# total dwell seconds (same as before)
total, _, _ = np.histogram2d(xs, ys, bins=[nx, ny],
                             range=[[x_min, x_max], [y_min, y_max]])
# seconds that were slow
slow_mask = speeds <= V0
slow,  _, _ = np.histogram2d(xs[slow_mask], ys[slow_mask],
                             bins=[nx, ny],
                             range=[[x_min, x_max], [y_min, y_max]])

ratio = np.divide(slow, total, out=np.zeros_like(total, float),
                  where=total > 0)

ratio[total < 100] = 0
counts = ratio                  # ← feed this to contourf
levels = np.linspace(0, 1, 40)  # 0 % … 100 %

#
# --------
# # Average speed
# V_free = 30 / 3.6
# # total dwell seconds per cell (same as before)
# total, _, _ = np.histogram2d(xs, ys, bins=[nx, ny],
#                              range=[[x_min, x_max], [y_min, y_max]])
#
# # accumulate sum of speeds (speed × 1 s)
# speed_sum, _, _ = np.histogram2d(xs, ys, bins=[nx, ny],
#                                  range=[[x_min, x_max], [y_min, y_max]],
#                                  weights=speeds)
#
# avg_speed = np.divide(speed_sum, total, out=np.zeros_like(total, float),
#                       where=total > 0)
# counts = avg_speed             # feed to contourf
# levels = np.linspace(0, V_free, 40)   # choose appropriate upper bound
# fade_cmap.set_under('white')   # make empty cells white


if has_scipy:
    counts = gaussian_filter(counts, sigma=0.8)   # isotropic blur in *cells*

# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 4. contour plot with colour-bar locked to Axes -----------------------------
xc = (xedges[:-1] + xedges[1:]) / 2
yc = (yedges[:-1] + yedges[1:]) / 2
X, Y = np.meshgrid(xc, yc, indexing='ij')

fig, ax = plt.subplots(figsize=(10, 4))
levels  = 20

cs = ax.contourf(X, Y, counts, levels=levels, cmap=fade_cmap, interpolate=True,
                 alpha=0.8, zorder=10)

# equal aspect so 1 unit X = 1 unit Y
ax.set_aspect('equal', adjustable='box')

# inset colour-bar exactly matching plot height
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
cax = inset_axes(ax, width="3%", height="100%",
                 loc="lower left", bbox_to_anchor=(1.02, 0., 1, 1),
                 bbox_transform=ax.transAxes, borderpad=0)
fig.colorbar(cs, cax=cax, label='Density (counts per cell)')

# plot x y points
ax.scatter(xs, ys, s=1, c='black', alpha=0.5, zorder=1)

ax.set_title('Congestion Heatmap')
ax.set_xlabel('X coordinate')
ax.set_ylabel('Y coordinate')
# fig.tight_layout()

# save as pdf
fig.savefig("heatmap.pdf", bbox_inches='tight', dpi=300)
plt.show()

# Replace contourf with pcolormesh for a pixelated look
# # Use pcolormesh instead of contourf
# cs = ax.pcolormesh(X, Y, counts, cmap=fade_cmap, shading='auto')
#
# # Equal aspect so 1 unit X = 1 unit Y
# ax.set_aspect('equal', adjustable='box')
#
# # Inset color-bar exactly matching plot height
# from mpl_toolkits.axes_grid1.inset_locator import inset_axes
# cax = inset_axes(ax, width="3%", height="100%",
#                  loc="lower left", bbox_to_anchor=(1.02, 0., 1, 1),
#                  bbox_transform=ax.transAxes, borderpad=0)
# fig.colorbar(cs, cax=cax, label='Density (counts per cell)')
#
# ax.set_title('Congestion Heatmap')
# ax.set_xlabel('X coordinate')
# ax.set_ylabel('Y coordinate')
# plt.show()

# histogram for speeds



