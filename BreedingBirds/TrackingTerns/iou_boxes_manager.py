
class iouBoxesManager:
    
    def _calc_iou_box_vs_box(self, box1, box2):
        # Extracting box1 coordinates
        x1 = box1['box']['x1']
        y1 = box1['box']['y1']
        x1_max = box1['box']['x2']
        y1_max = box1['box']['y2']
        
        # Calculating box1 width and height
        w1 = x1_max - x1
        h1 = y1_max - y1
        
        # Extracting box2 coordinates
        x2 = box2['box']['x1']
        y2 = box2['box']['y1']
        x2_max = box2['box']['x2']
        y2_max = box2['box']['y2']

        # Calculating box1 width and height
        w2 = x2_max - x2
        h2 = y2_max - y2
        
        # Calculating the coordinates of the intersection rectangle
        x_intersection = max(x1, x2)
        y_intersection = max(y1, y2)
        x_intersection_max = min(x1_max, x2_max)
        y_intersection_max = min(y1_max, y2_max)
        
        # Calculating the area of intersection
        intersection_area = max(0, x_intersection_max - x_intersection) * max(0, y_intersection_max - y_intersection)
        
        # Calculating the area of union
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - intersection_area
        
        # Calculating the IoU
        iou = intersection_area / union_area
        
        return iou    
    
    def calc_iou_box_vs_boxes_seq(self, boxes_sequence, box):
        if len(boxes_sequence) == 0:
            return 0

        # Calculating the Iou for my_box with each other_box
        ious = [self._calc_iou_box_vs_box(box, other_box) for other_box in boxes_sequence]
        # Return the average
        return sum(ious) / len(ious)
            

    def calc_iou_boxes_seq_vs_boxes_seq(self, box_sequence1, box_sequence2):
        if len(box_sequence1) == 0 or len(box_sequence2) == 0:
            return 0
        # Calculating the Iou for my_box with each other_box
        ious = [self.calc_iou_box_vs_boxes_seq(box_sequence1, box2) for box2 in box_sequence2]
        # Return the average
        return sum(ious) / len(ious)
    
    def calc_iou_boxes_seq_vs_boxes_sequences(self, box_sequence, box_sequences):
        if len(box_sequence) == 0:
            return 0
        ious = [self.calc_iou_boxes_seq_vs_boxes_seq(box_sequence, one_seq) for one_seq in box_sequences]
        # Return the average
        return sum(ious) / len(ious)
