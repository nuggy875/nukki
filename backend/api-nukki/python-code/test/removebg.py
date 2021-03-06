import cv2
import numpy as np
import os
import os.path as osp
import sys
from matplotlib import pyplot as plt

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
MASK_COLOR = (0.0,0.0,0.0) # In BGR format


def findContour(input_img, output_img):
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

    tmp = cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)
    _,alpha = cv2.threshold(tmp,0,255,cv2.THRESH_BINARY)
    b, g, r = cv2.split(masked)
    rgba = [b,g,r, alpha]
    dst = cv2.merge(rgba,4)

    #cv2.imshow('img', dst)                                   # Display
    #cv2.waitKey()
    cv2.imwrite(output_img, dst)           # Save


def grabCut(input_img, output_img):
    img = cv2.imread(input_img)
    w = img.shape[0]
    h = img.shape[1]
    print(w, h)
    # h x h 행렬
    mask = np.zeros(img.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    # rect = (1,1,655,344)
    x2 = img.shape[:2][1]
    y2 = img.shape[:2][0]
    shape = img.shape
    rect = (1, 1, int(img.shape[:2][1]), int(img.shape[:2][0]))
    cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)

    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
    img = img*mask2[:,:,np.newaxis]

    tmp = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, alpha = cv2.threshold(tmp, 0, 255, cv2.THRESH_BINARY)
    b, g, r = cv2.split(img)
    rgba = [b,g,r, alpha]
    dst = cv2.merge(rgba,4)

    #cv2.imshow('img', dst)                                   # Display
    #cv2.waitKey()
    cv2.imwrite(output_img, dst)           # Save


def watershed(input_img, output_img):
    img = cv2.imread(input_img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    
    #Morphology의 opening, closing을 통해서 노이즈나 Hole제거
    kernel = np.ones((3,3),np.uint8)
    opening = cv2.morphologyEx(thresh,cv2.MORPH_OPEN,kernel,iterations=2)

    # dilate를 통해서 확실한 Backgroud
    sure_bg = cv2.dilate(opening,kernel,iterations=3)

    #distance transform을 적용하면 중심으로 부터 Skeleton Image를 얻을 수 있음.
    # 즉, 중심으로 부터 점점 옅어져 가는 영상.
    # 그 결과에 thresh를 이용하여 확실한 FG를 파악
    dist_transform = cv2.distanceTransform(opening,cv2.DIST_L2,5)
    ret, sure_fg = cv2.threshold(dist_transform,0.5*dist_transform.max(),255,0)
    sure_fg = np.uint8(sure_fg)

    # Background에서 Foregrand를 제외한 영역을 Unknow영역으로 파악
    unknown = cv2.subtract(sure_bg, sure_fg)

    # FG에 Labelling작업
    ret, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0

    # watershed를 적용하고 경계 영역에 색지정
    markers = cv2.watershed(img,markers)
    img[markers == -1] = [255,0,0]

    images = [gray, thresh, sure_bg, dist_transform, sure_fg, unknown, markers, img]
    titles = ['Gray','Binary','Sure BG','Distance','Sure FG','Unknow','Markers','Result']

    for i in range(len(images)):
        plt.subplot(2, 4, i+1), plt.imshow(images[i]), plt.title(titles[i]), plt.xticks([]), plt.yticks([])

    # plt.show()
    cv2.imwrite(output_img, img)           # Save

def bgSubMOG2(input_img, output_img):
    fgbg = cv2.createBackgroundSubtractorMOG2()
    img = cv2.imread(input_img)
    fgmask = fgbg.apply(img)
    #cv2.imshow('fgmask', img)
    #cv2.waitKey()

    #cv2.imshow('frame', fgmask)
    #cv2.waitKey()
    cv2.imwrite(output_img, fgmask)           # Save


# python removebg.py 1 test5
# mode = 1
# imageFileName = test5

if __name__ == "__main__":
    '''
    if len(sys.argv) == 1 or len(sys.argv) == 2:
        print('ERROR:EnvVarialbleRequired')
        exit()
    '''
    # sys.argv[1]
    argv1 = '2'
    # sys.argv[2]
    argv2 = 'test2'

    input_img_path = osp.realpath('../public/image/'+argv2+'.jpg')
    det_path = osp.realpath('../public/result')
    if not os.path.exists(det_path):
        os.makedirs(det_path)
    output_img_path = osp.join(det_path, argv1+'_'+argv2+'_rst.png')

    if not os.path.exists(input_img_path):
        print('ERROR:ImageNotExists')
        exit()
    
    # findConcour 알고리즘 (OpenCV)
    if argv1 == '1':
        findContour(input_img_path, output_img_path)
    # grapcut 알고리즘 (OpenCV)
    elif argv1 == '2':
        grabCut(input_img_path, output_img_path)
    # watershed 알고리즘 (OpenCV)
    elif argv1 == '3':
        watershed(input_img_path, output_img_path)
    # BackgroundSubtractorMOG2 알고리즘 (OpenCV)
    elif argv1 == '4':
        bgSubMOG2(input_img_path, output_img_path)
    
    else:
        print('else')
        

    




