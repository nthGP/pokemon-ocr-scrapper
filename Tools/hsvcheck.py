import cv2
import numpy as np
from matplotlib import pyplot as plt

# Function to convert BGR to HSV and get the values of a pixel
def get_hsv_values(image, x, y):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv_value = hsv_image[y, x]  # Note: (y, x) instead of (x, y) for row-column indexing
    return hsv_value

# Mouse callback function to get the HSV value of a clicked pixel
def click_event(event, x, y, flags, param):
    image = param['image']
    if event == cv2.EVENT_LBUTTONDOWN:
        # Get HSV values at the clicked position
        hsv_value = get_hsv_values(image, x, y)
        print(f"Clicked at (x={x}, y={y}), HSV Value: {hsv_value}")

        # Draw a small circle around the clicked point for visualization
        cv2.circle(image, (x, y), 5, (0, 255, 0), 2)
        cv2.imshow("Image", image)

def main(image_path):
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        print("Error: Could not open image.")
        return

    # Show the image and wait for mouse clicks to get HSV values
    cv2.imshow("Image", image)
    print("Click on the image to get HSV values. Press 'q' to exit.")
    
    # Set the mouse callback to display HSV values on click
    cv2.setMouseCallback("Image", click_event, {'image': image})

    # Keep the window open until the user presses 'q'
    while True:
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up
    cv2.destroyAllWindows()

# Run the HSV testing script
if __name__ == "__main__":
    image_path = 'Pokemon/1.png'  # Replace with your icon screenshot path
    main(image_path)
