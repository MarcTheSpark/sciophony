observers_ojo_3840[] observer_ojo_3840;
int observerNum_ojo_3840;
import java.util.Arrays;

class observers_ojo_3840 {

  String[] lines_eyes_tracks_left_3840 = new String[0];
  String[] lines_eyes_tracks_chunks_left_3840 = new String[0];

  String[] lines_eyes_tracks_right_3840 = new String[0];
  String[] lines_eyes_tracks_chunks_right_3840 = new String[0];

  int cantidadLineas_left_3840; // number of lines in eye tracking data file for left eye
  int cantidadLineas_right_3840; //number of lines in eye tracking data file for right eye
  int cantidadLineas_3840;
  int lineCounter_3840;

  float EYE_X_left_3840, EYE_Y_left_3840;
  float EYE_X_right_3840, EYE_Y_right_3840;

  color cp_left_3840, cp_right_3840;
  color cp_left_3840_color;


  float blend_3840;

  int diam;

  int obs;

  float strWeight;
  
  float minX, maxX;


  void creaObserver_ojo_3840(int i) {

    obs = i;

    // retreives the eye tracking data for that particular cerver
    lines_eyes_tracks_left_3840 = loadStrings("../eyes_track_samples/tracks_3840/portrait_"+RETRATO_NUM+"/"+RETRATO_NUM+"_left/datos_"+obs+".txt");
    lines_eyes_tracks_right_3840 = loadStrings("../eyes_track_samples/tracks_3840/portrait_"+RETRATO_NUM+"/"+RETRATO_NUM+"_right/datos_"+obs+".txt");

    cantidadLineas_left_3840 = lines_eyes_tracks_left_3840.length;   // numer of lines
    cantidadLineas_right_3840 = lines_eyes_tracks_right_3840.length;

    cantidadLineas_3840 = min(cantidadLineas_left_3840, cantidadLineas_right_3840); // takes the min value of lines in case they were different
    //println(obs+",left: "+lines_eyes_tracks_left_3840.length+", right: "+lines_eyes_tracks_right_3840.length+" : "+cantidadLineas_3840); //imprime la cantidad de lineas del registro de cada observer

    lineCounter_3840 = 0;

    updatePositionValues();
  }
  
  void updatePositionValues() {
      lines_eyes_tracks_chunks_left_3840 = splitTokens(lines_eyes_tracks_left_3840[lineCounter_3840]);
      lines_eyes_tracks_chunks_right_3840 = splitTokens(lines_eyes_tracks_right_3840[lineCounter_3840]);

      float valueX_right_3840 =float(lines_eyes_tracks_chunks_right_3840[1]);
      float valueY_right_3840 = float(lines_eyes_tracks_chunks_right_3840[2]);
      float valueX_left_3840 = float(lines_eyes_tracks_chunks_left_3840[1]);
      float valueY_left_3840 = float(lines_eyes_tracks_chunks_left_3840[2]);

      // SWITCHING X and Y here
      EYE_X_left_3840 = map(valueX_left_3840, minDataX, maxDataX, 0, width);
      EYE_Y_left_3840 = map(valueY_left_3840, minDataY, maxDataY, 0, height);
      EYE_X_right_3840 = map(valueX_right_3840, minDataX, maxDataX, 0, width);
      EYE_Y_right_3840 = map(valueY_right_3840, minDataY, maxDataY, 0, height);
      
  }

  void countLine_3840(boolean useGlobalTime) {
    smooth();
    if (useGlobalTime) {
      lineCounter_3840 = int(currentTime / DATA_DT) % cantidadLineas_3840;
    } else {
      lineCounter_3840 = (lineCounter_3840 + 1) % cantidadLineas_3840;
    }
  }
  
}
