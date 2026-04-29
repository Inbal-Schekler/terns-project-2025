from iou_boxes_manager import iouBoxesManager

class TrackBoxesAcrossMovies:   
    # This function assosiate tracked objects of a scan with tracked objects from other scans
    # The assosiation means the tracked object from the different scan are of the same object
    def assosiate_tracked_objects(self, cur_tracked_objects, previous_tracked_objects, objects_assosiations, \
                                  iou_threshold = 0.08):
        prev_scans_number = len(previous_tracked_objects)
        # If the objects assosiations is empty then add all current tracked objects to objects assosiations 
        if len(objects_assosiations) == 0:
            return [[-1] * prev_scans_number + [i] for i in range(len(cur_tracked_objects))]

        iou_boxes_manager = iouBoxesManager()
        # This list tells if a sequence already found an object that belongs to it
        suit_object_found = [False] * len(objects_assosiations)
        # Loop through new objects to assosiate them with itself from other scans
        for cur_tracked_object_idx, cur_tracked_object in enumerate(cur_tracked_objects):
            # The ious of the tracked object against each tracked object sequence
            object_ious = []
            # Loop through all object sequences to check if the current object suits to one of them
            for idx, object_assosiation in enumerate(objects_assosiations):
                # If object already added to this sequence then we should avoid adding another object
                if suit_object_found[idx]:
                    object_ious.append(0)
                    continue
                
                iou_cnt, iou_sum = 0, 0
                for i in range(len(object_assosiation)):
                    object_index_in_specific_scan = object_assosiation[i]
                    # The value -1 means the object sequence did not found a suitable object in scan i
                    if object_index_in_specific_scan != -1:
                        iou_sum += iou_boxes_manager.calc_iou_boxes_seq_vs_boxes_seq(cur_tracked_object, \
                                                            previous_tracked_objects[i][object_index_in_specific_scan])
                        iou_cnt += 1

                iou = iou_sum / iou_cnt if iou_cnt > 0 else 0
                object_ious.append(iou)

            # Get the maximum iou index and value
            index, max_iou = max(enumerate(object_ious), key=lambda x: x[1])

            if max_iou >= iou_threshold:
                objects_assosiations[index].append(cur_tracked_object_idx)
                suit_object_found[index] = True
            else:
                new_onject_assosiation = [-1] * prev_scans_number + [cur_tracked_object_idx]
                objects_assosiations.append(new_onject_assosiation)
                suit_object_found.append(True)


        # Add index -1 to every object sequence that doesn't have suited object in the current tracked objects
        for objects_assosiation in objects_assosiations:
            if len(objects_assosiation) == prev_scans_number:
                objects_assosiation.append(-1)
        
        return objects_assosiations