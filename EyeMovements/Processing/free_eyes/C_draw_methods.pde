interface DrawMethod {
    void drawBG();
    void drawEye(int which, int EYE_X_LEFT, int EYE_Y_LEFT, int EYE_X_RIGHT, int EYE_Y_RIGHT);
}

class TranslucentCircles implements DrawMethod {
    int blend = 50;
    
    int DIAM_MIN = (int)(17 * SCALE);
    int DIAM_MAX = (int)(35 * SCALE);
    
    int[] eyeDiameters = new int[CANTIDAD_OBSERVERS_ojo_3840];

    {  // Instance initializer block (runs once when object is created)
        for (int i = 0; i < eyeDiameters.length; i++) {
            eyeDiameters[i] = (int) random(DIAM_MIN, DIAM_MAX);
        }
    }
    
    public void drawBG() {
        push();
        fill(0, 3);
        rect(-1, -1, width, height);
        pop();
    }
    
    public void drawEye(int i, int EYE_X_LEFT, int EYE_Y_LEFT, int EYE_X_RIGHT, int EYE_Y_RIGHT) {
        push();
        PImage img = LOADED_IMAGES.get("retrato_" +RETRATO_NUM + ".jpg");

        color pixelColor = img.get(EYE_X_LEFT, EYE_Y_LEFT);
        noStroke();
        fill(pixelColor, blend);
        ellipse(EYE_X_LEFT, EYE_Y_LEFT, eyeDiameters[i], eyeDiameters[i]);
        
        pixelColor = img.get(EYE_X_RIGHT, EYE_Y_RIGHT);
        noStroke();
        fill(pixelColor, blend);
        ellipse(EYE_X_RIGHT, EYE_Y_RIGHT, eyeDiameters[i], eyeDiameters[i]);
        pop();
    }
}


class DrawMethod2 implements DrawMethod {
    int diam = int(30 * SCALE);
    
    color[] eyeColors = {
      color(100, 103, 208),
      color(104, 166, 87),
      color(158, 120, 187),
      color(81, 212, 143),
      color(148, 136, 222),
      color(226, 99, 103),
      color(136, 98, 176),
      color(106, 147, 168),
      color(131, 113, 150),
      color(99, 105, 182),
      color(182, 81, 79),
      color(219, 153, 182),
      color(201, 186, 141),
      color(154, 129, 211),
      color(153, 228, 118),
      color(130, 209, 92),
      color(158, 183, 175),
      color(162, 148, 206),
      color(135, 87, 203),
      color(77, 204, 122),
      color(186, 164, 96),
      color(123, 89, 173),
      color(180, 129, 158),
      color(167, 95, 100),
      color(136, 125, 87),
      color(102, 189, 107),
      color(180, 112, 101),
      color(113, 221, 127),
      color(108, 89, 200),
      color(176, 183, 179),
      color(224, 144, 172),
      color(167, 103, 182),
      color(212, 183, 163),
      color(95, 216, 80),
      color(193, 127, 94),
      color(144, 141, 130),
      color(161, 132, 226),
      color(105, 105, 216),
      color(188, 208, 153),
      color(151, 103, 101),
      color(146, 88, 223),
      color(171, 218, 226),
      color(98, 186, 168),
      color(152, 152, 132),
      color(192, 214, 212),
      color(187, 160, 89),
      color(205, 178, 218),
      color(134, 150, 203),
      color(160, 190, 130),
      color(210, 116, 131),
    };

    /*
    {  // Initialize random colors
        for (int i = 0; i < eyeColors.length; i++) {
            eyeColors[i] = color(random(255), random(255), random(255));
        }
    }*/
    
    public void drawBG() {
        push();
        background(255);
        pop();
    }
    
    public void drawEye(int i, int EYE_X_LEFT, int EYE_Y_LEFT, int EYE_X_RIGHT, int EYE_Y_RIGHT) {
        push();

        noStroke();
        fill(eyeColors[i]);
        ellipse(EYE_X_LEFT, EYE_Y_LEFT, diam, diam);
        
        noStroke();
        fill(eyeColors[i]);
        ellipse(EYE_X_RIGHT, EYE_Y_RIGHT, diam, diam);
        pop();
    }
}

class DrawMethod3 extends DrawMethod2 {
      { diam = int(10 * SCALE); }
}

class CanvasCircles implements DrawMethod {
    int blend = 50;
    
    int DIAM_MIN = (int)(5 * SCALE);
    int DIAM_MAX = (int)(20 * SCALE);
    
    String CANVAS_IMG = "sheet4.jpg";
    int BACK_BLEND_RATIO = 5;
    int BLEND_BACKGROUND = 20;
    
    int FONT_SIZE = 11;
    int TXT_OVER = 12;
    
    int frameCounter = 0;
    
    int[] eyeDiameters = new int[CANTIDAD_OBSERVERS_ojo_3840];

    {  // Instance initializer block (runs once when object is created)
        for (int i = 0; i < eyeDiameters.length; i++) {
            eyeDiameters[i] = (int) random(DIAM_MIN, DIAM_MAX);
        }
    }
    
    public void drawBG() {
        push();
        if (frameCounter % BACK_BLEND_RATIO == 0) { // 4
          tint(255, 255, 255, BLEND_BACKGROUND);
          image(LOADED_IMAGES.get(CANVAS_IMG), 0, 0);
        }
        pop();
        frameCounter = (frameCounter + 1) % 4;
    }
    
    public void drawEye(int i, int EYE_X_LEFT, int EYE_Y_LEFT, int EYE_X_RIGHT, int EYE_Y_RIGHT) {
        push();
        noFill();
        strokeWeight(0.5);
        stroke(0, 0, 180, 190);
        ellipse(EYE_X_LEFT, EYE_Y_LEFT, eyeDiameters[i], eyeDiameters[i] );

        //if (dist(EYE_X_LEFT, EYE_Y_LEFT, EYE_X_1_left_3840, EYE_Y_1_left_3840) < diam * 0.0001) {
        //  if (lineCounter_3840 % 50 == 0) {

        //    textFont(LOADED_FONTS.get("AlTarikh-48.vlw"), FONT_SIZE);
        //    pushMatrix();
        //    float angle2 = radians(0);
        //    String label = (int(red(cp_left_3840))+","+int(green(cp_left_3840))+","+int(blue(cp_left_3840)));
        //    translate(EYE_X_LEFT - (2 * label.length()), EYE_Y_LEFT - TXT_OVER);
        //    rotate(angle2);
        //   // fill(250, 250, 250, 255);
        //   fill(0, 0, 160, 255);

        //    text(label, 0, 0);
        //    popMatrix();
        //  }
        //}
        pop();
    }
}

DrawMethod[] drawMethods = {
    new TranslucentCircles(),
    new CanvasCircles(),
    new DrawMethod2(),
    new DrawMethod3(),
};
