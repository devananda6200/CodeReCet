import openvino as ov
core = ov.Core()
try:
    model = core.read_model("d:/arakkunnam-99/model output/best_openvino_model/best.xml")
    print("Success!")
except Exception as e:
    print("Error:", e)
