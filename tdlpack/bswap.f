      SUBROUTINE BSWAP(NVAL)
C
C        SEPTEMBER 2004 WIEDENFELD   MDL   HP9000
C        JULY      2012 ENGLE        MDL   MODIFIED FOR MOS-2000
C
C        PURPOSE
C            TO BYTE SWAP AN INTEGER VALUE OF 4-BYTES.
C
C        DATA SET USE
C            NONE
C
C        VARIABLES
C                NVAL = THE INTEGER VALUE TO BE SWAPED.  (INPUT-OUTPUT)
C               NVALT = WORK VALUE TO DO BE EQUIVALENCED TO CVAL1. (INTERNAL)
C            CVAL1(4) = 1 BYTE CHARACTER ARRAY TO EQUAL THE 4 BYTES FROM THE
C                       INTEGER VALUE NVALT (INTERNAL)
C               CTEMP = TEMPERARAY PLACE HOLDER FOR SWAPPING. (INTERNAL)
C
C        NONSYSTEM SUBROUTINES CALLED
C           NONE
C
C
      REAL NVAL,NVALT
      CHARACTER*1 CVAL1(4),CTEMP
C     
      EQUIVALENCE(NVALT,CVAL1(1))
C
      NVALT=NVAL
C
      DO 110 I=1,2
         CTEMP=CVAL1(I)
         CVAL1(I)=CVAL1(5-I)
         CVAL1(5-I)=CTEMP
 110  CONTINUE
C
      NVAL=NVALT
C
      RETURN
      END
