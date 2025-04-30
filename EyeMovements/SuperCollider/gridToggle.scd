/**
Defines ~makeGridToggle, which makes a GUI Object (a UserView with a draw function) that lets you toggle on and off
squares in a grid. Returns an Event (pseudo-object) with various functions that let you set and observe the state of
that grid.
**/

~makeGridToggle = { |parent, dimensions, rows, cols, onColor=(Color.blue), offColor=(Color.gray(0.8))|
    var squareSize = Point(dimensions.x / cols, dimensions.y / rows);
    var gridState = Array.fill(rows * cols, { false });
    var numberOverlays = Array.fill(rows * cols, { 0 });
    var isDragging = false, dragState = nil;

    var gridView = UserView.new(parent)
    .drawFunc_({ |view|
        var ctx = Pen;
        var size = view.bounds.extent;
        squareSize = Point(size.x / cols, size.y / rows);
        rows.do { |r|
            cols.do { |c|
                var x = c * squareSize.x, y = r * squareSize.y;
                var idx = (r * cols) + c;
                ctx.fillColor = gridState[idx].if(onColor, offColor);
                ctx.fillRect(Rect(x, y, squareSize.x, squareSize.y));
                ctx.strokeColor = Color.black;
                ctx.strokeRect(Rect(x, y, squareSize.x, squareSize.y));

                // Draw number if greater than 0
                if (numberOverlays[idx] > 0) {
                    var fontSize = (squareSize.x.min(squareSize.y) * 0.5).asInteger;
                    ctx.font = Font("Helvetica", fontSize);
                    ctx.fillColor = Color.black;
                    ctx.stringCenteredIn(numberOverlays[idx].asString, Rect(x, y, squareSize.x, squareSize.y));
                }
            }
        };
    })
    .mouseDownAction_({ |view, x, y, btn|
        var r = (y / squareSize.y).asInteger;
        var c = (x / squareSize.x).asInteger;
        if (r < rows and: c < cols) {
            isDragging = true;
            dragState = gridState[(r * cols) + c].not;
            gridState[(r * cols) + c] = dragState;
            view.refresh;
        }
    })
    .mouseMoveAction_({ |view, x, y|
        if (isDragging) {
            var r = (y / squareSize.y).asInteger;
            var c = (x / squareSize.x).asInteger;
            if ((r >= 0) and: (r < rows) and: (c >= 0) and: (c < cols) and: (gridState[(r * cols) + c] != dragState)) {
                gridState[(r * cols) + c] = dragState;
                view.refresh;
            }
        }
    })
    .mouseUpAction_({ isDragging = false; });

    // Return an Event with functions to interact
    (
        view: gridView,
        state: gridState,
        unselectAll: {
            gridState = Array.fill(rows * cols, { false });
            gridView.refresh;
        },
        selectAll: {
            gridState = Array.fill(rows * cols, { true });
            gridView.refresh;
        },
        getSelected: {
            gridState.collect({ |x, i| if (x) { i } }).reject(_.isNil);
        },
        setNumberOverlays: { |e, newOverlays|
			newOverlays.do { |x, i|
				numberOverlays[i] = x;
			};
			AppClock.sched(0, { gridView.refresh });
        }
    )
};
