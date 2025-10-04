import io # io.BytesIO: lets you treat a memory buffer like a file.
import qrcode

def make_qr_png(url: str) -> bytes:
    img = qrcode.make(url)
    buf = io.BytesIO() # create an empty in-memory buffer.
    img.save(buf, format="PNG") # save the image into that buffer, as a PNG.
    return buf.getvalue() # return the raw bytes of the PNG.

# The router sets media_type="image/png", so browsers can display it.
