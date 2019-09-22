import cv2
import numpy as np
import os
import os.path as osp
import sys

#== Parameters =======================================================================
#BLUR = 21
#CANNY_THRESH_1 = 10
#CANNY_THRESH_2 = 200
#MASK_DILATE_ITER = 10
#MASK_ERODE_ITER = 10
#MASK_COLOR = (0.0,0.0,1.0) # In BGR format


BLUR = 5
CANNY_THRESH_1 = 10
CANNY_THRESH_2 = 10
MASK_DILATE_ITER = 10
MASK_ERODE_ITER = 10
MASK_COLOR = (1.0,1.0,1.0) # In BGR format




def cannyAlg(input_img):
    #== Processing =======================================================================

    #-- Read image -----------------------------------------------------------------------

    img = cv2.imread(input_img)
    # gray scaling
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


    #-- Edge detection -------------------------------------------------------------------
    edges = cv2.Canny(gray, CANNY_THRESH_1, CANNY_THRESH_2)
    edges = cv2.dilate(edges, None)
    edges = cv2.erode(edges, None)

    #-- Find contours in edges, sort by area ---------------------------------------------
    contour_info = []
    # Previously, for a previous version of cv2, this line was: 
    # _, contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    # Thanks to notes from commenters, I've updated the code but left this note
    for c in contours:
        contour_info.append((
            c,
            cv2.isContourConvex(c),
            cv2.contourArea(c),
        ))
    contour_info = sorted(contour_info, key=lambda c: c[2], reverse=True)
    max_contour = contour_info[0]

    #-- Create empty mask, draw filled polygon on it corresponding to largest contour ----
    # Mask is black, polygon is white
    mask = np.zeros(edges.shape)
    cv2.fillConvexPoly(mask, max_contour[0], (255))

    #-- Smooth mask, then blur it --------------------------------------------------------
    mask = cv2.dilate(mask, None, iterations=MASK_DILATE_ITER)
    mask = cv2.erode(mask, None, iterations=MASK_ERODE_ITER)
    mask = cv2.GaussianBlur(mask, (BLUR, BLUR), 0)
    mask_stack = np.dstack([mask]*3)    # Create 3-channel alpha mask

    #-- Blend masked img into MASK_COLOR background --------------------------------------
    mask_stack  = mask_stack.astype('float32') / 255.0          # Use float matrices, 
    img         = img.astype('float32') / 255.0                 #  for easy blending

    masked = (mask_stack * img) + ((1-mask_stack) * MASK_COLOR) # Blend
    masked = (masked * 255).astype('uint8')                     # Convert back to 8-bit 


    cv2.imshow('img', masked)                                   # Display
    cv2.waitKey()


    det_path = osp.realpath('../public/result')
    if not os.path.exists(det_path):
        os.makedirs(det_path)
    cv2.imwrite(osp.join(det_path, sys.argv[1]+'_rst.png'), masked)           # Save


def grabCut(input_img):
    


# python removebg.py 1 test5
# mode = 1
# imageFileName = test5

if __name__ == "__main__":
    if len(sys.argv) == 1 or len(sys.argv) == 2:
        print('ERROR:EnvVarialbleRequired')
        exit()
        
    input_img_path = osp.realpath('../public/image/'+sys.argv[2]+'.jpg')

    if not os.path.exists(input_img_path):
        print('ERROR:ImageNotExists')
        exit()
    
    if sys.argv[1] == '1':
        cannyAlg(input_img_path)
    elif sys.argv[2] == '2':
        grabCut(input_img_path)
    
    else:
        print('else')
        

    





    