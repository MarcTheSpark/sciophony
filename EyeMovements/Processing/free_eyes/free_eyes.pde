import oscP5.*;
import netP5.*;
import java.io.File;

HashMap<String, PImage> LOADED_IMAGES;
HashMap<String, PFont> LOADED_FONTS;

OscP5 oscP5;

boolean[] activeObservers;

DrawMethod currentDrawMethod;

void settings() {
  size (ANCHO_PANTALLA, ALTO_PANTALLA);
  oscP5 = new OscP5(this, 12000);
}

void setup() {
  LOADED_IMAGES = new HashMap<String, PImage>();
  LOADED_FONTS = new HashMap<String, PFont>();

  loadAllImages("images");
  loadAllFonts("fonts");

  observer_ojo_3840 = new observers_ojo_3840[CANTIDAD_OBSERVERS_ojo_3840]; 
  
  // creates the observer objects
  for (int i = 0; i < CANTIDAD_OBSERVERS_ojo_3840; i++) {
    observer_ojo_3840[i] = new observers_ojo_3840();
    observer_ojo_3840[i].creaObserver_ojo_3840(i + 1);
  }
  
  activeObservers = new boolean[CANTIDAD_OBSERVERS_ojo_3840];
  
  //for (int i = 0; i < CANTIDAD_OBSERVERS_ojo_3840; i++) {
  //  activeObservers[i] = true;
  //}
  
  currentDrawMethod = drawMethods[1];

  noCursor();
}


void loadAllImages(String folderName) {
  File folder = new File(dataPath(folderName));
  if (folder.isDirectory()) {
    for (File file : folder.listFiles()) {
      if (file.getName().toLowerCase().matches(".*\\.(jpg|png|gif|jpeg)")) {
        String relativePath = folderName + "/" + file.getName();
        PImage img = loadImage(relativePath);
        if (img != null) {
          img.resize(width, height);
          LOADED_IMAGES.put(file.getName(), img);
        }
      }
    }
  }
}


void loadAllFonts(String folderName) {
  File folder = new File(dataPath(folderName));
  if (folder.isDirectory()) {
    for (File file : folder.listFiles()) {
      if (file.getName().toLowerCase().endsWith(".vlw")) {
        String relativePath = folderName + "/" + file.getName();
        PFont font = loadFont(relativePath);
        if (font != null) {
          LOADED_FONTS.put(relativePath, font);
        }
      }
    }
  }
}

  

void oscEvent(OscMessage msg) {
  if (msg.checkAddrPattern("/eyes/rate")) {  // Check for the correct address
    if (msg.checkTypetag("f")) {  // Ensure it's a float
      playbackRate = msg.get(0).floatValue();  // Get the float value
      //println("Updated playbackRate to: " + playbackRate);
    } else {
      println("Unexpected data type for /eyes/rate");
    }
  } else if (msg.checkAddrPattern("/eyes/show")) {
    if (msg.checkTypetag("i")) {  // Ensure it's a float
      activeObservers[msg.get(0).intValue()] = true;  
    } else {
      println("Unexpected data type for /eyes/show");
    }
  } else if (msg.checkAddrPattern("/eyes/hide")) {
    if (msg.checkTypetag("i")) {  // Ensure it's a float
      activeObservers[msg.get(0).intValue()] = false;  
    } else {
      println("Unexpected data type for /eyes/hide");
    }
  } else if (msg.checkAddrPattern("/eyes/setTime")) {
    if (msg.checkTypetag("f")) {  // Ensure it's a float
      currentTime = msg.get(0).floatValue();
    } else {
      println("Unexpected data type for /eyes/setTime");
    }
  } else if (msg.checkAddrPattern("/eyes/drawMethod")) {
    if (msg.checkTypetag("i")) {  // Ensure it's an int
      currentDrawMethod = drawMethods[msg.get(0).intValue()];
    } else {
      println("Unexpected data type for /eyes/drawMethod");
    }
  }
}


void draw() {
  int currentMillis = millis();
  
  float dt = 0;
  if (lastMillis != -1) {
    dt = (currentMillis - lastMillis) * 0.001 * playbackRate;
  }
  
  lastMillis = currentMillis;
  currentDrawMethod.drawBG();

  for (int k = 0; k < SUBFRAME_FACTOR; k++) {
    currentTime += dt / SUBFRAME_FACTOR;
    for (int i = 0; i < CANTIDAD_OBSERVERS_ojo_3840; i = i+1) {
      observer_ojo_3840[i].countLine_3840(true);  /// reads the data line and prints the position for each observer
      if(activeObservers[i]) {
        observer_ojo_3840[i].updatePositionValues();
        currentDrawMethod.drawEye(
          i, 
          int(observer_ojo_3840[i].EYE_X_left_3840),
          int(observer_ojo_3840[i].EYE_Y_left_3840),
          int(observer_ojo_3840[i].EYE_X_right_3840),
          int(observer_ojo_3840[i].EYE_Y_right_3840)
        );
      }
    }
  }
}
