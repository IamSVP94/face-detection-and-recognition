import json
from pathlib import Path
import cv2
import torch
from collections import Counter
from src.count_metrics import find_iou_for_all_boxes

PARENT_DIR = Path(__file__).parent.parent.resolve()  # root repo dir


def read_markups(directory_with_markup, filename):
    f = open(directory_with_markup + '/' + filename.split('.')[0] + '.json')
    data = json.load(f)
    true_bboxes = [sum(data['shapes'][i]['points'], []) for i, _ in enumerate(data['shapes'])]
    return true_bboxes


def draw_face(img, landmarks, colores, labels=None, scores=None, threshold=None, show=False):
    dimg = img.copy()

    text = f'found {len(landmarks)} faces'
    if threshold:
        text = f'{text} (threshold={threshold})'

    cv2.putText(dimg, text, (25, 25), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 255, 0), 1)
    for face_idx, face in enumerate(landmarks.values()):
        score, bbox, landmark = face.values()

        xmin, ymin, xmax, ymax = bbox
        cv2.rectangle(dimg, (int(xmin), int(ymin)), (int(xmax), int(ymax)), colores[face_idx], 1)

        bbox_text = f'{round(score, 4)}'
        if scores:
            bbox_text = f'{bbox_text} dist={(int(scores[face_idx]))}'
        if labels:
            bbox_text = f'{bbox_text} "{labels[face_idx]}"'

        cv2.putText(dimg, bbox_text, (int(xmin), int(ymin) - 7),
                    cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.9, colores[face_idx], 1)
        for point_name, point in landmark.items():
            if point_name in ['right_eye', 'mouth_right']:
                landmark_color = (0, 255, 255)
            else:
                landmark_color = (255, 0, 255)
            cv2.circle(dimg, tuple(map(int, point)), 1, landmark_color, 1)
    if show:
        cv2.imshow('Image', dimg)
        cv2.waitKey()
    return dimg


def draw_face_old(img, landmarks, labels=None, scores=None, threshold=None, show=False, color='green'):
    if color == 'blue':
        color = (255, 0, 0)
    elif color == 'red':
        color = (0, 0, 255)
    elif color == 'green':
        color = (0, 255, 0)
    dimg = img.copy()

    text = f'found {len(landmarks)} faces'
    if threshold:
        text = f'{text} (threshold={threshold})'

    cv2.putText(dimg, text, (25, 25), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 255, 0), 1)
    for face_idx, face in enumerate(landmarks.values()):
        score, bbox, landmark = face.values()

        xmin, ymin, xmax, ymax = bbox
        cv2.rectangle(dimg, (int(xmin), int(ymin)), (int(xmax), int(ymax)), color, 1)

        bbox_text = f'{round(score, 4)}'
        if scores:
            bbox_text = f'{bbox_text} dist={(int(scores[face_idx]))}'
        if labels:
            bbox_text = f'{bbox_text} "{labels[face_idx]}"'

        cv2.putText(dimg, bbox_text, (int(xmin), int(ymin) - 7),
                    cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.9, color, 1)
        for point_name, point in landmark.items():
            if point_name in ['right_eye', 'mouth_right']:
                landmark_color = (0, 255, 255)
            else:
                landmark_color = (255, 0, 255)
            cv2.circle(dimg, tuple(map(int, point)), 1, landmark_color, 1)
    if show:
        cv2.imshow('Image', dimg)
        cv2.waitKey()
    return dimg


def intersection_over_union(boxes_preds: list, boxes_labels: list, box_format: str = "midpoint") -> torch.Tensor:
    """
    Calculates intersection over union
    Parameters:
        boxes_preds (list): Predictions of Bounding Boxes (BATCH_SIZE, 4)
        boxes_labels (list): Correct Labels of Boxes (BATCH_SIZE, 4)
        box_format (str): midpoint/corners, if boxes (x,y,w,h) or (x1,y1,x2,y2)
    Returns:
        tensor: Intersection over union for all examples
    """
    if boxes_preds == boxes_labels and boxes_labels == []:
        return torch.Tensor([1])
    elif boxes_preds != boxes_labels and (boxes_preds == [] or boxes_labels == []):
        return torch.Tensor([0])

    # Slicing idx:idx+1 in order to keep tensor dimensionality
    boxes_preds = torch.Tensor(boxes_preds)
    boxes_labels = torch.Tensor(boxes_labels)

    # Doing ... in indexing if there would be additional dimensions
    # Like for Yolo algorithm which would have (N, S, S, 4) in shape
    if box_format == "midpoint":
        box1_x1 = boxes_preds[..., 1:2] - boxes_preds[..., 3:4] / 2
        box1_y1 = boxes_preds[..., 2:3] - boxes_preds[..., 4:5] / 2
        box1_x2 = boxes_preds[..., 1:2] + boxes_preds[..., 3:4] / 2
        box1_y2 = boxes_preds[..., 2:3] + boxes_preds[..., 4:5] / 2

        box2_x1 = boxes_labels[..., 1:2] - boxes_labels[..., 3:4] / 2
        box2_y1 = boxes_labels[..., 2:3] - boxes_labels[..., 4:5] / 2
        box2_x2 = boxes_labels[..., 1:2] + boxes_labels[..., 3:4] / 2
        box2_y2 = boxes_labels[..., 2:3] + boxes_labels[..., 4:5] / 2
    elif box_format == "corners":
        box1_x1 = boxes_preds[..., 0:1]
        box1_y1 = boxes_preds[..., 1:2]
        box1_x2 = boxes_preds[..., 2:3]
        box1_y2 = boxes_preds[..., 3:4]
        box2_x1 = boxes_labels[..., 0:1]
        box2_y1 = boxes_labels[..., 1:2]
        box2_x2 = boxes_labels[..., 2:3]
        box2_y2 = boxes_labels[..., 3:4]

    x1 = torch.max(box1_x1, box2_x1)
    y1 = torch.max(box1_y1, box2_y1)
    x2 = torch.min(box1_x2, box2_x2)
    y2 = torch.min(box1_y2, box2_y2)

    # Need clamp(0) in case they do not intersect, then we want intersection to be 0
    intersection = (x2 - x1).clamp(0) * (y2 - y1).clamp(0)
    box1_area = abs((box1_x2 - box1_x1) * (box1_y2 - box1_y1))
    box2_area = abs((box2_x2 - box2_x1) * (box2_y2 - box2_y1))

    final_iou = intersection / (box1_area + box2_area - intersection + 1e-6)
    return final_iou


def mean_average_precision(pred_boxes: list, true_boxes: list,
                           iou_threshold=0.5,
                           box_format: str = "midpoint",
                           num_classes: int = 1) -> float:
    """
    Calculates mean average precision
    Parameters:
        pred_boxes (list): list of lists containing all bboxes with each bboxes
        specified as [train_idx, class_prediction, prob_score, x1, y1, x2, y2]
        true_boxes (list): Similar as pred_boxes except all the correct ones
        iou_threshold (float): threshold where predicted bboxes is correct
        box_format (str): "midpoint" or "corners" used to specify bboxes
        num_classes (int): number of classes
    Returns:
        float: mAP value across all classes given a specific IoU threshold
    """
    if pred_boxes == true_boxes and true_boxes == []:
        return 1.0
    elif pred_boxes != true_boxes and (pred_boxes == [] or true_boxes == []):
        return 0.0

    # list storing all AP for respective classes
    average_precisions = []

    # used for numerical stability later on
    epsilon = 1e-6

    for c in range(num_classes):
        detections = []
        ground_truths = []

        # Go through all predictions and targets,
        # and only add the ones that belong to the
        # current class c
        for detection in pred_boxes:
            if detection[0] == c:
                detections.append(detection)

        for true_box in true_boxes:
            if true_box[0] == c:
                ground_truths.append(true_box)

        # find the amount of bboxes for each training example
        # Counter here finds how many ground truth bboxes we get
        # for each training example, so let's say img 0 has 3,
        # img 1 has 5 then we will obtain a dictionary with:
        # amount_bboxes = {0:3, 1:5}
        amount_bboxes = Counter([gt[0] for gt in ground_truths])  # +

        # We then go through each key, val in this dictionary
        # and convert to the following (w.r.t same example):
        # ammount_bboxes = {0:torch.tensor[0,0,0], 1:torch.tensor[0,0,0,0,0]}
        for key, val in amount_bboxes.items():  # - ???
            amount_bboxes[key] = torch.zeros(val)

        # sort by box probabilities which is index 2
        detections.sort(key=lambda x: x[2], reverse=True)
        TP = torch.zeros((len(detections)))
        FP = torch.zeros((len(detections)))
        total_true_bboxes = len(ground_truths)

        # If none exists for this class then we can safely skip
        if total_true_bboxes == 0:
            continue

        for detection_idx, detection in enumerate(detections):
            # Only take out the ground_truths that have the same
            # training idx as detection
            ground_truth_img = [bbox for bbox in ground_truths if bbox[0] == detection[0]]

            num_gts = len(ground_truth_img)
            best_iou = 0

            for idx, gt in enumerate(ground_truth_img):
                # iou = intersection_over_union(detection, gt, box_format=box_format)
                _, _, iou = find_iou_for_all_boxes([detection], [gt])
                if iou[-1] > best_iou:
                    best_iou = iou[-1]
                    best_gt_idx = idx

            if best_iou > iou_threshold:
                # only detect ground truth detection once
                if amount_bboxes[detection[0]][best_gt_idx] == 0:
                    # true positive and add this bounding box to seen
                    TP[detection_idx] = 1
                    amount_bboxes[detection[0]][best_gt_idx] = 1
                else:
                    FP[detection_idx] = 1

            # if IOU is lower then the detection is a false positive
            else:
                FP[detection_idx] = 1

        TP_cumsum = torch.cumsum(TP, dim=0)
        FP_cumsum = torch.cumsum(FP, dim=0)
        recalls = TP_cumsum / (total_true_bboxes + epsilon)
        precisions = TP_cumsum / (TP_cumsum + FP_cumsum + epsilon)

        precisions = torch.cat((torch.tensor([1.0]), precisions))
        recalls = torch.cat((torch.tensor([0.0]), recalls))
        # torch.trapz for numerical integration
        average_precisions.append(torch.trapz(precisions, recalls))

    final_map = sum(average_precisions) / len(average_precisions)
    return float(final_map)


def get_GT_bbox(txt_path):
    with open(txt_path, 'r') as txt:
        lines = txdetect_model = RetinaFace.build_model()
        t.readlines()
        GT = []
        for line in lines:
            line = line.strip('\n').split(' ')
            cl, x, y, w, h = line
            GT.append([int(cl), float(x), float(y), float(w), float(h)])
    return GT


def bbox2yolobbox(img, box):  # box = (left, top, right, bottom)
    original_h, original_w, _ = img.shape
    xmin, ymin, xmax, ymax = box['facial_area']

    dw = 1. / original_w
    dh = 1. / original_h

    x = (xmin + xmax) / 2.0
    y = (ymin + ymax) / 2.0
    w = xmax - xmin
    h = ymax - ymin

    x = round(x * dw, 6)
    y = round(y * dh, 6)
    w = round(w * dw, 6)
    h = round(h * dh, 6)
    yolo_format = [0, x, y, w, h]  # 0 because only 1 class
    return yolo_format


def yolobbox2bbox(img, bbox):
    cl, x, y, w, h = bbox
    original_h, original_w, _ = img.shape

    xmin = original_w * (x - w / 2)
    ymin = original_h * (y - h / 2)
    xmax = original_w * (x + w / 2)
    ymax = original_h * (y + h / 2)
    return [cl, int(xmin), int(ymin), int(xmax), int(ymax)]


def write_label(txt_path, bboxes):
    with open(txt_path, 'w') as txt:
        into_file = []
        for bbox in bboxes:
            cl, x, y, w, h = bbox
            into_file.append(f'{cl} {x} {y} {w} {h}\n')
        txt.writelines(into_file)
