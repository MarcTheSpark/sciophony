(

this.executeFile("gridToggle.scd".resolveRelative);

~setupGUI = {
	arg sonificationNames, launchCallback, endCallback, endAllCallback;
	var win, mainBox, listView, selectButtons, buttons, label, paddingFactor, baseFontSize;
	var gridToggle, selectAllButton, selectNoneButton;


	paddingFactor = 0.05; // 5% padding
	baseFontSize = 14;    // Base font size for reference

	~guiWin.notNil.if{~guiWin.close};
	~guiWin = win = Window("GUI Window", Rect(100, 100, 800, 600), resizable: true)
	.alwaysOnTop_(false) // Allow full-screening
	.front;

	win.view.background = Color.black;

	// Main container
	mainBox = CompositeView(win, Rect(100, 100, 600, 400))
	.background_(Color.white);

	gridToggle = ~makeGridToggle.(mainBox, 500@150, 3, 10);

	listView = ListView(mainBox, 200@200)
	.items_(sonificationNames)
	.fixedHeight_(260);

	selectButtons = [
		Button(mainBox, 100@300).states_([["Select All"]]).action_({gridToggle.selectAll}),
		Button(mainBox, Rect(0, 0, 1, 0.1)).states_([["Select None"]]).action_({gridToggle.unselectAll})
	];

	buttons = [
		Button(mainBox, Rect(0, 0, 1, 0.5)).states_([["LAUNCH"]]).action_({launchCallback.(gridToggle.getSelected)}),
		Button(mainBox, Rect(0, 0, 1, 0.1)).states_([["END"]]).action_({endCallback.(gridToggle.getSelected)}),
		Button(mainBox, Rect(0, 0, 1, 0.1)).states_([["END ALL"]]).action_({endAllCallback.(gridToggle.getSelected)})
	];


	// Function to update layout dynamically
	win.view.onResize_({ |view|
		var size = view.bounds.extent;
		var minSide = size.asArray.minItem; // Ensure square aspect ratio
		var padding = minSide * paddingFactor;
		var mainSize = minSide - (2 * padding);
		var scaledFontSize = (mainSize * 0.03).clip(10, 30); // Scale between 10-30 pts

		// Update main box position and size
		mainBox.bounds = Rect(
			(size.x - mainSize) * 0.5, // Center horizontally
			(size.y - mainSize) * 0.5, // Center vertically
			mainSize,
			mainSize
		);
		listView.fixedHeight_(mainSize * 0.56);

		buttons.do {
			|btn|
			btn.font = Font("Helvetica", scaledFontSize);
			btn.fixedSize_(Point(mainSize * 0.2, mainSize * 0.15));
		};
		selectButtons.do  {
			|btn|
			btn.font = Font("Helvetica", scaledFontSize);
			btn.fixedSize_(Point(mainSize * 0.25, mainSize * 0.08));
		};
		listView.font = Font("Helvetica", scaledFontSize);
	});

	mainBox.layout = VLayout(
		HLayout(selectButtons[0], selectButtons[1]).margins_(0),
		gridToggle.view,
		HLayout(listView, VLayout(buttons[0], buttons[1], buttons[2])),
	).margins_(20).spacing_(20);

	win.front;
	(
		unselectAllStreams: {gridToggle.unselectAll},
		selectAllStreams: {gridToggle.selectAll},
		getSelectedStreams: {gridToggle.getSelected},
		getSonificationMethod: {listView.items[listView.value]},
		gridToggle: {gridToggle}
	)
};
)
