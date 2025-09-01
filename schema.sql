
/* Run this once on your MSSQL server (SSMS/sqlcmd) on the target database */

IF OBJECT_ID('dbo.Stok', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.Stok (
        StokID      INT IDENTITY(1,1) PRIMARY KEY,
        MalzemeKod  NVARCHAR(50) NOT NULL,
        Kalite      NVARCHAR(50) NULL,
        BoyMM       INT NULL,
        Adet        INT NOT NULL CHECK (Adet >= 0),
        OlusturmaTS DATETIME2(3) DEFAULT SYSDATETIME()
    );
    CREATE INDEX IX_Stok_MalzemeKaliteBoy ON dbo.Stok(MalzemeKod, Kalite, BoyMM);
END
GO

CREATE OR ALTER PROCEDURE dbo.Sp_StokEkleVeyaArtir
    @MalzemeKod NVARCHAR(50),
    @Kalite     NVARCHAR(50) = NULL,
    @BoyMM      INT          = NULL,
    @Eklenecek  INT
AS
BEGIN
    SET NOCOUNT ON;
    IF @Eklenecek <= 0
        THROW 50001, 'Eklenecek adet > 0 olmalı', 1;

    IF EXISTS (
        SELECT 1 FROM dbo.Stok
        WHERE MalzemeKod=@MalzemeKod
          AND ISNULL(Kalite,'')=ISNULL(@Kalite,'')
          AND ISNULL(BoyMM,0)=ISNULL(@BoyMM,0)
    )
    BEGIN
        UPDATE dbo.Stok
        SET Adet = Adet + @Eklenecek
        WHERE MalzemeKod=@MalzemeKod
          AND ISNULL(Kalite,'')=ISNULL(@Kalite,'')
          AND ISNULL(BoyMM,0)=ISNULL(@BoyMM,0);
    END
    ELSE
    BEGIN
        INSERT INTO dbo.Stok(MalzemeKod,Kalite,BoyMM,Adet)
        VALUES (@MalzemeKod,@Kalite,@BoyMM,@Eklenecek);
    END;
END
GO

CREATE OR ALTER FUNCTION dbo.Fn_StokAra
(
   @Aranan NVARCHAR(100)
)
RETURNS TABLE
AS
RETURN
(
   SELECT StokID, MalzemeKod, Kalite, BoyMM, Adet, OlusturmaTS
   FROM dbo.Stok
   WHERE MalzemeKod LIKE '%' + @Aranan + '%'
);
GO

CREATE OR ALTER VIEW dbo.Vw_StokOzet
AS
SELECT MalzemeKod,
       Kalite,
       BoyMM,
       SUM(Adet) AS ToplamAdet
FROM dbo.Stok
GROUP BY MalzemeKod, Kalite, BoyMM;
GO
