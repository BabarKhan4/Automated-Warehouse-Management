(define (problem warehouse-delivery)
 (:domain warehouse)

 (:objects
  r1 r2 - robot
  p2 p3 - package
  zone_0_0 zone_0_1 zone_0_2 zone_0_3 zone_0_4 zone_0_5 zone_0_6 zone_1_0 zone_1_1 zone_1_2 zone_1_6 zone_2_0 zone_2_2 zone_2_4 zone_2_6 zone_3_0 zone_3_2 zone_3_3 zone_3_4 zone_3_6 zone_4_0 zone_4_2 zone_4_6 zone_5_0 zone_5_2 zone_5_3 zone_5_4 zone_5_6 zone_6_0 zone_6_2 zone_6_3 zone_6_4 zone_6_6 - location
 )

 ;; (:init removed by Reset — regenerate via generator)


 (:goal (and
  (at-package p2 zone_3_3)
  (at-package p3 zone_4_0)
 ))
)
