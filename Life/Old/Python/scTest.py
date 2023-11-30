from pythonosc.udp_client import SimpleUDPClient

sc_osc_client = SimpleUDPClient("localhost", 57120)

sc_osc_client.send_message("/shells/start", None)
sc_osc_client.send_message("/shells/heights", [36]*36)
