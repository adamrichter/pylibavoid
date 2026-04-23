"""Route an orthogonal connector around a fixed obstacle.

Run as a marimo notebook:

    marimo edit examples/routing_around_obstacle.py

Or export it to a standalone HTML:

    marimo export html examples/routing_around_obstacle.py -o /tmp/demo.html

Requires libavoid_py (installed from this repo), marimo, and
matplotlib in the active Python environment. This file lives on
the ``examples/marimo-demo`` branch; it is not shipped with the
package.
"""

import marimo

__generated_with = "0.23.2"
app = marimo.App()


@app.cell
def _intro():
    import marimo as mo

    mo.md(
        """
        # Routing around an obstacle

        libavoid is an incremental orthogonal connector router. The
        classic demo is: two rectangles want to be connected, a third
        rectangle sits between them. libavoid produces an orthogonal
        path from one endpoint to the other that does not cross any
        shape's interior.

        This notebook builds that scene with the phase-2 wrapper
        surface — `Router`, `ShapeRef`, `ConnRef`, `ConnEnd`,
        `Rectangle`, `Point` — processes a single routing transaction,
        and plots the resulting polyline.
        """
    )
    return (mo,)


@app.cell
def _scene():
    import libavoid_py as la

    router = la.Router(la.RouterFlag.OrthogonalRouting)

    # Two rectangles on opposite sides of the canvas.
    left_box = la.Rectangle(la.Point(0, 0), la.Point(40, 20))
    right_box = la.Rectangle(la.Point(140, 0), la.Point(180, 20))
    la.ShapeRef(router, left_box)
    la.ShapeRef(router, right_box)

    # An obstacle sitting in the middle, directly between them.
    obstacle_box = la.Rectangle(la.Point(80, -5), la.Point(110, 25))
    la.ShapeRef(router, obstacle_box)

    # Connector from the right edge of the left box to the left edge
    # of the right box. Without the obstacle this would be a straight
    # horizontal line; with it, libavoid nudges the path up or down.
    src = la.ConnEnd(la.Point(40, 10))
    dst = la.ConnEnd(la.Point(140, 10))
    conn = la.ConnRef(router, src, dst)

    router.process_transaction()
    route = conn.display_route()
    return left_box, obstacle_box, right_box, route


@app.cell
def _render(left_box, obstacle_box, right_box, route):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle as MplRect

    fig, ax = plt.subplots(figsize=(8, 4))

    shapes = [
        (left_box, "tab:blue", "A"),
        (right_box, "tab:blue", "B"),
        (obstacle_box, "tab:red", "obstacle"),
    ]
    for poly, colour, label in shapes:
        min_x = min(p.x for p in poly)
        max_x = max(p.x for p in poly)
        min_y = min(p.y for p in poly)
        max_y = max(p.y for p in poly)
        ax.add_patch(
            MplRect(
                (min_x, min_y),
                max_x - min_x,
                max_y - min_y,
                facecolor=colour,
                edgecolor=colour,
                alpha=0.25,
                linewidth=2,
            )
        )
        ax.text(
            (min_x + max_x) / 2,
            (min_y + max_y) / 2,
            label,
            ha="center",
            va="center",
            color=colour,
            fontsize=10,
            fontweight="bold",
        )

    xs = [p.x for p in route]
    ys = [p.y for p in route]
    ax.plot(xs, ys, color="black", linewidth=2, marker="o", markersize=4)

    ax.set_aspect("equal")
    ax.set_xlim(-10, 200)
    ax.set_ylim(-30, 50)
    ax.grid(True, alpha=0.3)
    ax.set_title("Orthogonal route around a fixed obstacle")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    return


@app.cell
def _route_report(mo, route):
    points = [(p.x, p.y) for p in route]
    mo.md(
        f"""
        ## Route

        libavoid produced a polyline with **{len(points)} vertices**:

        ```
        {points}
        ```
        """
    )
    return


if __name__ == "__main__":
    app.run()
